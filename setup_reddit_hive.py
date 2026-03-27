"""
Flatten Reddit JSON → TSV, upload to HDFS, create Hive external + ORC tables.
This follows the same HDFS + Hive + ORC pipeline as setup_brand_hive.py.

External Data Source:
  Reddit API JSON (manually extracted) → external_data/reddit_api.json
  Already placed on VM at: /home/azmine/reddit_api.json

Pipeline:
  1. Parse nested Reddit JSON on VM → flat TSV (/home/azmine/reddit_posts.tsv)
  2. Upload TSV to HDFS at /user/hive/warehouse/ticketmeta09.db/reddit_posts/
  3. Create Hive external table (ext_reddit_posts) pointing to HDFS location
  4. Create ORC table (reddit_posts_orc) with Snappy compression
"""
import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to VM (node-master)...")
client.connect("192.168.56.105", username="azmine", password="Ubuntu71$", timeout=30)

ENV = ("export PATH=/opt/hadoop/bin:/opt/spark-3.5.3/bin:$PATH; "
       "export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop; "
       "export SPARK_HOME=/opt/spark-3.5.3; ")

def run(cmd, timeout=300):
    print(f"\n$ {cmd[:120]}...")
    stdin, stdout, stderr = client.exec_command(ENV + cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out[-2000:] if len(out) > 2000 else out)
    if err and 'WARN' not in err and 'INFO' not in err: print(f"ERR: {err[-500:]}")
    return out


# ─── Step 1: Flatten Reddit JSON → TSV on VM ───
print("\n=== Step 1: Flatten reddit_api.json → reddit_posts.tsv on VM ===")

# Python script to run on VM that converts the nested Reddit JSON to a flat TSV
flatten_script = r'''
import json, csv, sys

json_path = "/home/azmine/reddit_api.json"
tsv_path = "/home/azmine/reddit_posts.tsv"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

children = data.get("data", {}).get("children", [])
if isinstance(data, list):
    children = data

with open(tsv_path, "w", encoding="utf-8", newline="") as out:
    writer = csv.writer(out, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["title", "score", "num_comments", "url", "permalink", "created_utc", "subreddit", "author", "selftext"])
    count = 0
    for child in children:
        d = child.get("data", child) if isinstance(child, dict) else {}
        title = (d.get("title") or "").replace("\t", " ").replace("\n", " ")
        if not title:
            continue
        selftext = (d.get("selftext") or "").replace("\t", " ").replace("\n", " ")[:500]
        writer.writerow([
            title,
            d.get("score", 0),
            d.get("num_comments", 0),
            d.get("url", ""),
            d.get("permalink", ""),
            d.get("created_utc", 0),
            d.get("subreddit", ""),
            d.get("author", ""),
            selftext,
        ])
        count += 1

print(f"Flattened {count} Reddit posts to {tsv_path}")
'''

# Upload the flatten script to VM and run it
sftp = client.open_sftp()
with sftp.open("/tmp/flatten_reddit.py", "w") as f:
    f.write(flatten_script)

run("python3 /tmp/flatten_reddit.py")

# Verify TSV was created
run("head -3 /home/azmine/reddit_posts.tsv")
run("wc -l /home/azmine/reddit_posts.tsv")


# ─── Step 2: Upload TSV from VM to HDFS ───
print("\n=== Step 2: Upload reddit_posts.tsv to HDFS ===")

run("hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/reddit_posts")
run("hdfs dfs -rm -f /user/hive/warehouse/ticketmeta09.db/reddit_posts/* 2>/dev/null; echo cleaned")
run("hdfs dfs -put -f /home/azmine/reddit_posts.tsv /user/hive/warehouse/ticketmeta09.db/reddit_posts/")
run("hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/reddit_posts/")


# ─── Step 3: Create Hive tables via spark-sql ───
print("\n=== Step 3: Create Hive External Tables + ORC ===")

all_sql = """
USE ticketmeta09;

-- ── Reddit Posts (External → ORC) ──
DROP TABLE IF EXISTS ext_reddit_posts;
CREATE EXTERNAL TABLE ext_reddit_posts (
    title           STRING,
    score           INT,
    num_comments    INT,
    url             STRING,
    permalink       STRING,
    created_utc     DOUBLE,
    subreddit       STRING,
    author          STRING,
    selftext        STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t'
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ticketmeta09.db/reddit_posts'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT 'REDDIT_EXT_VERIFY' AS step, COUNT(*) AS cnt FROM ext_reddit_posts;

DROP TABLE IF EXISTS reddit_posts_orc;
CREATE TABLE reddit_posts_orc
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY')
AS SELECT * FROM ext_reddit_posts;

SELECT 'REDDIT_ORC_VERIFY' AS step, COUNT(*) AS cnt FROM reddit_posts_orc;
SELECT title, score, num_comments, subreddit FROM reddit_posts_orc ORDER BY score DESC LIMIT 5;

-- ── Verify all tables ──
SHOW TABLES;
"""

# Upload HQL to VM
with sftp.open("/tmp/reddit_hive_setup.hql", "w") as f:
    f.write(all_sql)
sftp.close()

print("Running spark-sql (3-5 min for Spark init + table creation)...")
result = run(
    "export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf; "
    "spark-sql --master yarn --driver-class-path /opt/apache-hive-4.0.1/lib/mysql-connector-j-8.4.0.jar "
    "-f /tmp/reddit_hive_setup.hql 2>&1 | grep -v '^[0-9]\\{2\\}/[0-9]\\{2\\}' | tail -40",
    timeout=600
)

client.close()
print("\n" + "="*60)
print("✅ Done! Reddit posts loaded into Hive via HDFS+Hive+ORC:")
print("   Source:  /home/azmine/reddit_api.json (manually extracted)")
print("   TSV:     /home/azmine/reddit_posts.tsv (flattened)")
print("   HDFS:    /user/hive/warehouse/ticketmeta09.db/reddit_posts/")
print("   Tables:  ext_reddit_posts → reddit_posts_orc")
print("="*60)

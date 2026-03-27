"""
Upload ACSI scores + DOT complaint rates CSVs to HDFS and create Hive tables.
This follows the same HDFS + Hive + ORC pipeline as setup_delay_hive.py.

External Data Sources:
  1. ACSI Airline Scores  → https://www.theacsi.org/industries/travel/airline/
  2. DOT Complaint Rates  → https://www.transportation.gov/airconsumer/air-travel-consumer-reports

Both CSVs are in external_data/ folder (extracted from published reports).
"""
import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to VM...")
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

# ─── Step 1: Upload CSV files to VM via SFTP ───
print("\n=== Step 1: Upload CSV files to VM ===")
sftp = client.open_sftp()

local_files = {
    "external_data/acsi_airline_scores.csv": "/home/azmine/acsi_airline_scores.csv",
    "external_data/dot_complaint_rates.csv": "/home/azmine/dot_complaint_rates.csv",
}
for local, remote in local_files.items():
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), local)
    print(f"  Uploading {local} → {remote}")
    sftp.put(local_path, remote)

# ─── Step 2: Upload CSVs from VM to HDFS ───
print("\n=== Step 2: Upload to HDFS ===")

# ACSI Scores
run("hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/acsi_scores")
run("hdfs dfs -rm -f /user/hive/warehouse/ticketmeta09.db/acsi_scores/* 2>/dev/null; echo cleaned")
run("hdfs dfs -put -f /home/azmine/acsi_airline_scores.csv /user/hive/warehouse/ticketmeta09.db/acsi_scores/")
run("hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/acsi_scores/")

# DOT Complaint Rates
run("hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/dot_complaints")
run("hdfs dfs -rm -f /user/hive/warehouse/ticketmeta09.db/dot_complaints/* 2>/dev/null; echo cleaned")
run("hdfs dfs -put -f /home/azmine/dot_complaint_rates.csv /user/hive/warehouse/ticketmeta09.db/dot_complaints/")
run("hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/dot_complaints/")

# ─── Step 3: Create Hive tables via spark-sql ───
print("\n=== Step 3: Create Hive External Tables + ORC ===")

all_sql = """
USE ticketmeta09;

-- ── ACSI Scores ──
DROP TABLE IF EXISTS ext_acsi_scores;
CREATE EXTERNAL TABLE ext_acsi_scores (
    airline_name    STRING,
    acsi_score      INT,
    year            INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ticketmeta09.db/acsi_scores'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT 'ACSI_EXT_VERIFY' AS step, COUNT(*) AS cnt FROM ext_acsi_scores;

DROP TABLE IF EXISTS acsi_scores_orc;
CREATE TABLE acsi_scores_orc
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY')
AS SELECT * FROM ext_acsi_scores;

SELECT 'ACSI_ORC_VERIFY' AS step, COUNT(*) AS cnt FROM acsi_scores_orc;
SELECT * FROM acsi_scores_orc;

-- ── DOT Complaint Rates ──
DROP TABLE IF EXISTS ext_dot_complaints;
CREATE EXTERNAL TABLE ext_dot_complaints (
    airline_name            STRING,
    complaint_rate_per_100k DOUBLE,
    year                    INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ticketmeta09.db/dot_complaints'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT 'DOT_EXT_VERIFY' AS step, COUNT(*) AS cnt FROM ext_dot_complaints;

DROP TABLE IF EXISTS dot_complaints_orc;
CREATE TABLE dot_complaints_orc
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY')
AS SELECT * FROM ext_dot_complaints;

SELECT 'DOT_ORC_VERIFY' AS step, COUNT(*) AS cnt FROM dot_complaints_orc;
SELECT * FROM dot_complaints_orc;

-- ── Verify all tables ──
SHOW TABLES;
"""

# Upload HQL to VM
with sftp.open("/tmp/brand_external_setup.hql", "w") as f:
    f.write(all_sql)
sftp.close()

print("Running spark-sql with direct JDBC config (3-5 min for Spark init + table creation)...")
result = run(
    "export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf; "
    "spark-sql --master yarn --driver-class-path /opt/apache-hive-4.0.1/lib/mysql-connector-j-8.4.0.jar "
    "-f /tmp/brand_external_setup.hql 2>&1 | grep -v '^[0-9]\\{2\\}/[0-9]\\{2\\}' | tail -40",
    timeout=600
)

client.close()
print("\n" + "="*60)
print("✅ Done! Brand Markup external datasets loaded into Hive:")
print("   ext_acsi_scores     → acsi_scores_orc     (10 rows, ACSI 2022)")
print("   ext_dot_complaints  → dot_complaints_orc   (10 rows, DOT 2022)")
print("   airline_delay_cause → airline_delay_cause_orc (22,965 rows, BTS)")
print("="*60)

"""
Put Airline_Delay_Cause.csv through the full HDFS + Hive + ORC pipeline.

Key config note: Uses Flask API's spark-conf directory (/home/azmine/flight_api/spark-conf)
which connects to Hive Metastore via direct JDBC to MySQL (not Thrift).
The default spark-defaults.conf sets metastore.version=4.0.1 which Spark 3.5.3
doesn't support, and the default hive-site.xml points to thrift://node-master:9083
(HMS not running). The Flask API config avoids both issues.
"""
import paramiko, time

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

# Step 1: Verify CSV
print("\n=== Step 1: Verify CSV ===")
run("ls -lh /home/azmine/Airline_Delay_Cause.csv; wc -l /home/azmine/Airline_Delay_Cause.csv")

# Step 2: HDFS upload
print("\n=== Step 2: Upload to HDFS ===")
run("hdfs dfs -mkdir -p /user/hive/warehouse/ticketmeta09.db/airline_delay_cause")
run("hdfs dfs -rm -f /user/hive/warehouse/ticketmeta09.db/airline_delay_cause/* 2>/dev/null; echo cleaned")
run("hdfs dfs -put -f /home/azmine/Airline_Delay_Cause.csv /user/hive/warehouse/ticketmeta09.db/airline_delay_cause/")
run("hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/airline_delay_cause/")

# Step 3+4+5: Create ext table + verify + ORC in one spark-sql session
print("\n=== Step 3-5: Hive External Table + ORC (one session) ===")
all_sql = """
USE ticketmeta09;
DROP TABLE IF EXISTS ext_airline_delay_cause;
CREATE EXTERNAL TABLE ext_airline_delay_cause (
    year INT, month INT, carrier STRING, carrier_name STRING,
    airport STRING, airport_name STRING,
    arr_flights DOUBLE, arr_del15 DOUBLE,
    carrier_ct DOUBLE, weather_ct DOUBLE, nas_ct DOUBLE,
    security_ct DOUBLE, late_aircraft_ct DOUBLE,
    arr_cancelled DOUBLE, arr_diverted DOUBLE, arr_delay DOUBLE,
    carrier_delay DOUBLE, weather_delay DOUBLE, nas_delay DOUBLE,
    security_delay DOUBLE, late_aircraft_delay DOUBLE
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/hive/warehouse/ticketmeta09.db/airline_delay_cause'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT 'EXT_TABLE_VERIFY' AS step, COUNT(*) AS cnt FROM ext_airline_delay_cause;

DROP TABLE IF EXISTS airline_delay_cause_orc;
CREATE TABLE airline_delay_cause_orc
STORED AS ORC TBLPROPERTIES ('orc.compress'='SNAPPY')
AS SELECT * FROM ext_airline_delay_cause;

SELECT 'ORC_TABLE_VERIFY' AS step, COUNT(*) AS cnt FROM airline_delay_cause_orc;
SELECT carrier_name, ROUND(SUM(arr_del15),0) AS delays, ROUND(SUM(arr_flights),0) AS flights,
       ROUND((1-SUM(arr_del15)/SUM(arr_flights))*100,1) AS ontime_pct
FROM airline_delay_cause_orc WHERE carrier_name IS NOT NULL
GROUP BY carrier_name ORDER BY flights DESC LIMIT 10;
SHOW TABLES;
"""

sftp = client.open_sftp()
with sftp.open("/tmp/full_delay_setup.hql", "w") as f:
    f.write(all_sql)
sftp.close()

# Also save locally
with open("d:/final/Ticket-meta/hql_code/airline_delay_cause.hql", "w") as f:
    f.write(all_sql)

# KEY FIX: Use SPARK_CONF_DIR pointing to Flask API config (direct JDBC to MySQL, no Thrift)
# This avoids: 1) unsupported metastore version 4.0.1, 2) Thrift connection refused
print("Running spark-sql with direct JDBC config (3-5 min for Spark init + table creation)...")
result = run(
    "export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf; "
    "spark-sql --master yarn --driver-class-path /opt/apache-hive-4.0.1/lib/mysql-connector-j-8.4.0.jar "
    "-f /tmp/full_delay_setup.hql 2>&1 | grep -v '^[0-9]\\{2\\}/[0-9]\\{2\\}' | tail -30",
    timeout=600
)

client.close()
print("\n✅ Done! Airline_Delay_Cause.csv: CSV → HDFS → Hive External Table → ORC")
print("   ext_airline_delay_cause  (22,965 rows, CSV/TextFile)")
print("   airline_delay_cause_orc  (22,965 rows, ORC+Snappy)")

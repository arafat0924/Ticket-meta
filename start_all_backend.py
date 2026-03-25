"""Start all backend services on the VM after reboot."""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to node-master...")
client.connect("node-master", username="azmine", password="Ubuntu71$", timeout=120)

def ssh(cmd, t=60):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=t)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out: print(f"  {out[:1500]}")
    if err and 'warning' not in err.lower() and 'WARN' not in err: print(f"  ERR: {err[:500]}")
    return out

# 1. Start HDFS
print("\n===== 1. Starting HDFS =====")
ssh("export HADOOP_HOME=/opt/hadoop && $HADOOP_HOME/sbin/start-dfs.sh", t=30)
time.sleep(10)

# 2. Start YARN
print("\n===== 2. Starting YARN =====")
ssh("export HADOOP_HOME=/opt/hadoop && $HADOOP_HOME/sbin/start-yarn.sh", t=30)
time.sleep(10)

# 3. Check HDFS is healthy
print("\n===== 3. Checking HDFS =====")
ssh("HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop /opt/hadoop/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/ 2>/dev/null | head -5")

# 4. Check MySQL (Hive Metastore DB)
print("\n===== 4. Checking MySQL =====")
ssh("systemctl is-active mysql 2>/dev/null || sudo systemctl start mysql; echo 'MySQL:' $(systemctl is-active mysql)")

# 5. Start Flask API
print("\n===== 5. Starting Flask API =====")
ssh("pkill -9 -f flask_api 2>/dev/null; sleep 1")
startup = '''#!/bin/bash
export SPARK_HOME=/opt/spark-3.5.3
export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
export HIVE_METASTORE_URIS=""
export SPARK_MASTER="local[*]"
cd /home/azmine/flight_api
truncate -s 0 api.log
nohup python3 flask_api.py > api.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! && echo "RUNNING" || echo "FAILED"
'''
ssh(f"cat > /tmp/start_api.sh << 'EOF'\n{startup}\nEOF")
ssh("bash /tmp/start_api.sh", t=15)

# Wait for Spark init
print("\n===== Waiting 60s for Spark initialization =====")
time.sleep(60)

# 6. Verify everything
print("\n===== 6. Verification =====")
ssh("jps 2>/dev/null | grep -v Jps")
health = ssh("curl -s --max-time 15 http://localhost:5000/api/health?deep=1")
print(f"\nAPI Health: {health}")

if '"connected"' in health:
    print("\n✅ All backend services are UP!")
else:
    print("\n⏳ API is still warming up. Give it another 30-60 seconds.")

client.close()

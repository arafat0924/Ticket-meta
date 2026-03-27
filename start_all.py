import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.56.104", username="arafat", password="092424", timeout=60)

def ssh(cmd, t=30):
    print(f"$ {cmd}")
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(f"  {out[:600]}")
    if err and "WARN" not in err and "WARNING" not in err and "deprecat" not in err.lower():
        if err.strip(): print(f"  ERR: {err[:300]}")
    return out

ENV = """
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop-3.3.6
export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop
export SPARK_HOME=/opt/spark-3.5.3
export HIVE_HOME=/opt/apache-hive-4.0.1
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$HIVE_HOME/bin:$PATH
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
"""

# Kill everything first
print("=== Killing old processes ===")
ssh("pkill -9 -f flask_api 2>/dev/null; pkill -9 -f SparkSubmit 2>/dev/null; sleep 2")

# Step 1: Start HDFS
print("\n=== Starting HDFS ===")
ssh(f"{ENV} start-dfs.sh", t=30)
time.sleep(5)

# Step 2: Start YARN
print("\n=== Starting YARN ===")
ssh(f"{ENV} start-yarn.sh", t=30)
time.sleep(5)

# Step 3: Verify Hadoop
print("\n=== Checking services ===")
ssh("jps")

# Step 4: Check if Hive metastore is running
print("\n=== Checking Hive Metastore ===")
out = ssh("jps | grep RunJar")
if "RunJar" not in out:
    print("  Starting Hive Metastore...")
    ssh(f"{ENV} nohup hive --service metastore > /tmp/metastore.log 2>&1 &", t=10)
    time.sleep(10)
    ssh("jps | grep RunJar")
else:
    print("  Hive Metastore already running")

# Step 5: Check HDFS is accessible
print("\n=== Checking HDFS ===")
ssh(f"{ENV} hdfs dfs -ls /user 2>&1 | head -5", t=15)

# Step 6: Start Flask API
print("\n=== Starting Flask API ===")
startup = f"""
{ENV}
cd /home/arafat
nohup python3 flask_api.py > api.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! 2>/dev/null && echo "RUNNING" || echo "FAILED"
"""
ssh(startup, t=15)

print("\nWaiting 90s for Spark init...")
time.sleep(90)

# Verify
health = ssh("curl -s --max-time 30 http://localhost:5000/api/health")
if '"connected"' in health:
    print(f"\n✅ Backend ready! Health: {health}")
else:
    print(f"\n⏳ Health: {health}")
    ssh("tail -15 /home/arafat/api.log")

c.close()
print("\n🎉 Done!")

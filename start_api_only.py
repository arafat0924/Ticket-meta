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
    return out

# Check if already running
out = ssh("curl -s --max-time 5 http://localhost:5000/api/health 2>/dev/null")
if '"connected"' in out:
    print("\n✅ Backend already running!")
    c.close()
    exit(0)

# Kill old flask
ssh("pkill -9 -f flask_api 2>/dev/null; pkill -9 -f SparkSubmit 2>/dev/null; sleep 2")

# Start Flask API with proper env
startup = """
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop-3.3.6
export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop
export SPARK_HOME=/opt/spark-3.5.3
export HIVE_HOME=/opt/apache-hive-4.0.1
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$HIVE_HOME/bin:$PATH
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
cd /home/arafat
nohup python3 flask_api.py > api.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! 2>/dev/null && echo "RUNNING" || echo "FAILED"
"""
ssh(startup, t=15)

print("\nWaiting 90s for Spark init...")
time.sleep(90)

health = ssh("curl -s --max-time 30 http://localhost:5000/api/health")
if '"connected"' in health:
    print(f"\n✅ Backend ready! {health}")
else:
    print(f"\n⏳ Health: {health}")
    ssh("tail -10 /home/arafat/api.log")

c.close()

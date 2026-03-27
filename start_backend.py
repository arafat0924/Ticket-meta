"""Start the Flask API backend on the VM."""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.56.104", username="arafat", password="092424", timeout=60)

def ssh(cmd, t=30):
    print(f"$ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=t)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out: print(f"  {out[:1500]}")
    if err and 'warning' not in err.lower(): print(f"  ERR: {err[:300]}")
    return out

# Check if already running
out = ssh("curl -s --max-time 5 http://localhost:5000/api/health 2>/dev/null")
if '"connected"' in out:
    print("\n✅ Backend is ALREADY running!")
    client.close()
    exit(0)

# Kill any stale processes
ssh("pkill -9 -f flask_api 2>/dev/null; pkill -9 -f SkyQuery 2>/dev/null; sleep 2")
ssh("rm -rf /tmp/blockmgr-* /tmp/spark-* 2>/dev/null")

# Start fresh
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

print("\nWaiting 60s for Spark initialization...")
time.sleep(60)

# Verify
health = ssh("curl -s --max-time 15 http://localhost:5000/api/health?deep=1")
if '"connected"' in health:
    print("\n✅ Backend started successfully! Health: connected")
else:
    print(f"\n⏳ Backend still warming up. Health: {health}")
    print("  (First request may take 20-30s while Spark finishes init)")

client.close()

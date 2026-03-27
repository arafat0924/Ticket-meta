"""Deploy updated flask_api.py to VM and restart backend."""
import paramiko, time

VM = "192.168.56.104"
USER = "arafat"
PASS = "092424"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VM, username=USER, password=PASS, timeout=30)

def ssh(cmd, t=30):
    print(f"$ {cmd}")
    _, o, e = client.exec_command(cmd, timeout=t)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(f"  {out[:800]}")
    if err and "warning" not in err.lower() and "deprecat" not in err.lower():
        print(f"  ERR: {err[:300]}")
    return out

# Step 1: Upload updated flask_api.py via SFTP
print("=== Uploading flask_api.py to VM ===")
sftp = client.open_sftp()
sftp.put("d:/Internship/web/flask_api.py", "/home/arafat/flask_api.py")
sftp.close()
print("  ✅ Uploaded successfully")

# Step 2: Kill existing Flask API
print("\n=== Stopping old backend ===")
ssh("pkill -9 -f flask_api 2>/dev/null; pkill -9 -f java 2>/dev/null; sleep 3")
ssh("rm -rf /tmp/blockmgr-* /tmp/spark-* /tmp/hsperfdata_* 2>/dev/null")

# Step 3: Start fresh
print("\n=== Starting Flask API ===")
startup = """cd /home/arafat
export SPARK_HOME=/opt/spark-3.5.3
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
export PATH=$SPARK_HOME/bin:$PATH
nohup python3 flask_api.py > api.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! 2>/dev/null && echo "RUNNING" || echo "FAILED"
"""
ssh(startup, t=15)

print("\nWaiting 90s for Spark initialization...")
time.sleep(90)

# Step 4: Verify
health = ssh("curl -s --max-time 30 http://localhost:5000/api/health")
if '"connected"' in health:
    print(f"\n✅ Backend started! Health: {health}")
else:
    print(f"\n⏳ Still warming up. Health: {health}")
    ssh("tail -15 /home/arafat/api.log")

client.close()
print("\n🎉 Done! Backend running at http://192.168.56.104:5000")

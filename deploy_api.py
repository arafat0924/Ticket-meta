"""Deploy updated flask_api.py to VM based on discovered config."""
import paramiko
import time
import sys

VM_IP = "192.168.56.101"
VM_USER = "vboxuser"
VM_PASS = "12345678"
API_PATH = "/home/vboxuser/flask_api.py"
API_DIR = "/home/vboxuser"
LOG_FILE = "flask.log"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {VM_IP}...")
client.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
print("Connected!")

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip()

# Upload flask_api.py
print("\nUploading flask_api.py...")
sftp = client.open_sftp()
sftp.put("d:/Internship/Final project/webapp/flask_api.py", API_PATH)
print("✓ Uploaded to", API_PATH)

try:
    sftp.put("d:/Internship/Final project/webapp/Airline_Delay_Cause.csv", f"{API_DIR}/Airline_Delay_Cause.csv")
    print("✓ CSV uploaded")
except:
    print("⚠ CSV upload skipped")
sftp.close()

# Verify new endpoints exist
count = run(f"grep -c 'nonstop-premium' {API_PATH}")
print(f"✓ New analytics endpoints verified: {count} matches")

# Kill old API
print("\nKilling old API process...")
run("pkill -9 -f flask_api 2>/dev/null; sleep 2")
print("✓ Old process killed")

# Use existing start_flask.sh or create new one
print("\nChecking start_flask.sh...")
existing = run("cat /home/vboxuser/start_flask.sh 2>/dev/null")
print(f"Existing script:\n{existing}")

# Restart using the existing startup approach
print("\nStarting API...")
script = """#!/bin/bash
export SPARK_HOME=/opt/spark-3.5.3
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export HIVE_HOME=/opt/apache-hive-4.0.1
export PYTHONPATH=$SPARK_HOME/python:$(ls $SPARK_HOME/python/lib/py4j-*-src.zip 2>/dev/null | head -1)
export PATH=$SPARK_HOME/bin:$HADOOP_CONF_DIR/../../bin:$HIVE_HOME/bin:$PATH
cd /home/vboxuser
truncate -s 0 flask.log 2>/dev/null || true
nohup python3 flask_api.py > flask.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! 2>/dev/null && echo "RUNNING" || echo "FAILED"
"""

sftp2 = client.open_sftp()
with sftp2.open("/tmp/start_api.sh", "w") as f:
    f.write(script)
sftp2.close()

result = run("bash /tmp/start_api.sh")
print(result)

print("\nWaiting 90s for Spark initialization...")
time.sleep(90)

health = run("curl -s --max-time 20 http://localhost:5000/api/health")
print(f"\nHealth: {health}")

if not health or "error" in str(health).lower():
    print(f"\nLast 20 lines of flask.log:")
    print(run(f"tail -20 {API_DIR}/{LOG_FILE}"))

client.close()
print("\nDone!")

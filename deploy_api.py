"""Upload updated flask_api.py + CSV to VM and restart the API."""
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to VM...")
client.connect("192.168.56.105", username="azmine", password="Ubuntu71$", timeout=30)

# Upload files
print("Uploading flask_api.py...")
sftp = client.open_sftp()
sftp.put("d:/final/Ticket-meta/flask_api.py", "/home/azmine/flight_api/flask_api.py")
print("Uploading Airline_Delay_Cause.csv...")
sftp.put("d:/final/Ticket-meta/Airline_Delay_Cause.csv", "/home/azmine/flight_api/Airline_Delay_Cause.csv")
sftp.close()
print("Upload complete!")

# Verify
stdin, stdout, stderr = client.exec_command("grep -c enrichment /home/azmine/flight_api/flask_api.py", timeout=10)
print(f"Enrichment endpoints count: {stdout.read().decode().strip()}")

# Install requests
stdin, stdout, stderr = client.exec_command("pip3 install requests 2>&1 | tail -2", timeout=30)
print(f"requests: {stdout.read().decode().strip()}")

# Restart
print("\nRestarting Flask API...")
stdin, stdout, stderr = client.exec_command("pkill -9 -f flask_api 2>/dev/null; sleep 2; echo killed", timeout=15)
print(stdout.read().decode().strip())

script = (
    "#!/bin/bash\n"
    "export SPARK_HOME=/opt/spark-3.5.3\n"
    "export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf\n"
    "export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop\n"
    "export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip\n"
    'export HIVE_METASTORE_URIS=""\n'
    "cd /home/azmine/flight_api\n"
    "truncate -s 0 api.log\n"
    "nohup python3 flask_api.py > api.log 2>&1 &\n"
    'echo "PID=$!"\n'
    "sleep 3\n"
    'kill -0 $! && echo "RUNNING" || echo "FAILED"\n'
)

# Write script via sftp
sftp2 = client.open_sftp()
with sftp2.open("/tmp/start_api.sh", "w") as f:
    f.write(script)
sftp2.close()

stdin, stdout, stderr = client.exec_command("bash /tmp/start_api.sh", timeout=15)
print(stdout.read().decode().strip())

print("\nWaiting 90s for Spark initialization...")
time.sleep(90)

stdin, stdout, stderr = client.exec_command("curl -s --max-time 20 http://localhost:5000/api/health", timeout=30)
health = stdout.read().decode().strip()
print(f"Health: {health}")

if not health:
    stdin, stdout, stderr = client.exec_command("tail -15 /home/azmine/flight_api/api.log", timeout=10)
    print(f"Log tail:\n{stdout.read().decode().strip()}")

client.close()
print("\nDone!")

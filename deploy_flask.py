import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# Upload flask_api.py
sftp = c.open_sftp()
sftp.put('d:/Internship/web/flask_api.py', '/home/arafat/flask_api.py')
sftp.close()
print("Uploaded flask_api.py")

# Kill any old Flask API
c.exec_command('pkill -f "python.*flask_api" 2>/dev/null', timeout=5)
time.sleep(2)

# Start Flask API in background
cmd = (
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
    'export SPARK_HOME=/opt/spark-3.5.3 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'export PYTHONPATH=/opt/spark-3.5.3/python:/opt/spark-3.5.3/python/lib/py4j-0.10.9.7-src.zip && '
    'cd /home/arafat && '
    'nohup python3 flask_api.py > /home/arafat/flask_api.log 2>&1 &'
)
c.exec_command(cmd, timeout=5)
print("Started Flask API")

time.sleep(10)
_, o, _ = c.exec_command('ps aux | grep flask_api | grep -v grep | wc -l', timeout=10)
print(f"Flask processes: {o.read().decode().strip()}")

_, o, _ = c.exec_command('tail -5 /home/arafat/flask_api.log 2>/dev/null', timeout=10)
print(f"Log: {o.read().decode().strip()[:300]}")

c.close()

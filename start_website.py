import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# 1. Kill any leftover spark/flask processes
print("Cleaning up...")
c.exec_command('pkill -f spark-submit 2>/dev/null; pkill -f flask_api 2>/dev/null', timeout=5)
time.sleep(3)

# 2. Clean partial ORC data
print("Cleaning partial ORC...")
c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -rm -r /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>/dev/null',
    timeout=15
)
time.sleep(2)

# 3. Check services
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; jps 2>/dev/null', timeout=10)
jps = o.read().decode().strip()
print(f"Services: {jps}")

# 4. Start Flask API (it will use CSV table since ORC doesn't exist)
print("\nStarting Flask API...")
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
print("Launched Flask API, waiting 30s for Spark init...")
time.sleep(30)

_, o, _ = c.exec_command('ps aux | grep flask_api | grep -v grep | wc -l', timeout=10)
count = o.read().decode().strip()
print(f"Flask processes: {count}")

_, o, _ = c.exec_command('tail -5 /home/arafat/flask_api.log 2>/dev/null', timeout=10)
print(f"Log: {o.read().decode().strip()[:400]}")

c.close()
print("\nDone!")

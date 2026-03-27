import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# 1. Upload updated optimize_orc.py
sftp = c.open_sftp()
sftp.put('d:/Internship/web/optimize_orc.py', '/home/arafat/optimize_orc.py')
print("Uploaded optimize_orc.py (1 executor, 1g driver)")
sftp.close()

# 2. Check Hadoop/YARN are running
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; /opt/hadoop-3.3.6/bin/yarn node -list 2>/dev/null | head -5', timeout=30)
print("YARN nodes:", o.read().decode().strip()[:300])

# 3. Start ORC optimization
cmd = (
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
    'export SPARK_HOME=/opt/spark-3.5.3 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'cd /home/arafat && '
    'nohup /opt/spark-3.5.3/bin/spark-submit --master yarn --deploy-mode client optimize_orc.py '
    '> /home/arafat/orc_optimize.log 2>&1 &'
)
c.exec_command(cmd, timeout=10)
print("Started ORC optimization")

time.sleep(5)
_, o, _ = c.exec_command('head -3 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Log:", o.read().decode().strip()[:200])

c.close()
print("Done!")

import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# Quick JPS check
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; jps 2>/dev/null | sort', timeout=10)
print("Services:", o.read().decode().strip())

# Quick HDFS check 
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/ 2>&1 | head -3',
    timeout=15
)
print("\nHDFS:", o.read().decode().strip()[:200])

# Launch ORC 
cmd = (
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
    'export SPARK_HOME=/opt/spark-3.5.3 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'cd /home/arafat && '
    'nohup spark-submit --master yarn --deploy-mode client '
    '--driver-memory 1g --executor-memory 2g --num-executors 1 --executor-cores 2 '
    'optimize_orc.py > /home/arafat/orc_optimize.log 2>&1 &'
)
c.exec_command(cmd, timeout=10)
print("\nLaunched ORC job, waiting 20s...")
time.sleep(20)

_, o, _ = c.exec_command('wc -l /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Log lines:", o.read().decode().strip())

_, o, _ = c.exec_command('tail -3 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Last:", o.read().decode().strip()[:300])

c.close()

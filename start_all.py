import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# Kill any old spark
c.exec_command('pkill -f spark-submit 2>/dev/null', timeout=5)

# Start HDFS
print("Starting HDFS...")
_, o, e = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    '$HADOOP_HOME/sbin/start-dfs.sh 2>&1',
    timeout=60
)
try:
    print(o.read().decode().strip()[:400])
except: pass

time.sleep(5)

# Start Hive metastore
print("\nStarting Hive metastore...")
c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'nohup $HIVE_HOME/bin/hive --service metastore > /tmp/metastore.log 2>&1 &',
    timeout=10
)
time.sleep(10)

# Check services
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; jps', timeout=10)
print("JPS:", o.read().decode().strip())

# Check HDFS
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/ 2>&1 | head -5',
    timeout=15
)
print("\nHDFS:", o.read().decode().strip()[:300])

# Start ORC job
print("\nStarting ORC conversion...")
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
time.sleep(15)

_, o, _ = c.exec_command('wc -l /home/arafat/orc_optimize.log 2>/dev/null; tail -5 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("\nORC Log:", o.read().decode().strip()[:500])

c.close()
print("\nDone!")

import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# 1. Remove the old partial ORC data
print("Removing old partial ORC data...")
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -rm -r /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>&1',
    timeout=30
)
print(o.read().decode().strip()[:300])

# 2. Also drop the Hive table metadata if it exists
print("\nDropping old table metadata...")
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    'export HIVE_HOME=/opt/apache-hive-4.0.1; '
    '$HIVE_HOME/bin/beeline -u "jdbc:hive2://" -e "DROP TABLE IF EXISTS ticketmeta09.itineraries_orc" 2>&1 | tail -3',
    timeout=30
)
try:
    print(o.read().decode().strip()[:200])
except: print("(beeline timed out - OK)")

# 3. Verify it's gone
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>&1',
    timeout=15
)
print("\nVerify removed:", o.read().decode().strip()[:200])

# 4. Launch ORC job
print("\nLaunching ORC conversion...")
cmd = (
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
    'export SPARK_HOME=/opt/spark-3.5.3 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'cd /home/arafat && '
    'nohup /opt/spark-3.5.3/bin/spark-submit --master yarn --deploy-mode client '
    '--driver-memory 1g --executor-memory 2g --num-executors 1 --executor-cores 2 '
    'optimize_orc.py > /home/arafat/orc_optimize.log 2>&1 &'
)
c.exec_command(cmd, timeout=5)
print("Launched!")

time.sleep(20)
_, o, _ = c.exec_command('tail -3 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Log:", o.read().decode().strip()[:300])

c.close()

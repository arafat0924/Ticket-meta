import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# 1. Kill Flask API and any Spark jobs to free ALL resources
print("Killing Flask API and any Spark jobs...")
c.exec_command('pkill -f flask_api 2>/dev/null; pkill -f spark-submit 2>/dev/null; pkill -f SparkSubmit 2>/dev/null', timeout=10)
time.sleep(5)

# 2. Kill any YARN applications
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    'for appid in $(/opt/hadoop-3.3.6/bin/yarn application -list 2>/dev/null | grep application_ | awk "{print \\$1}"); do '
    '/opt/hadoop-3.3.6/bin/yarn application -kill $appid 2>/dev/null; done',
    timeout=15
)
print("Killed YARN apps:", o.read().decode().strip()[:200])
time.sleep(3)

# 3. Clean partial ORC data
print("Cleaning partial ORC data...")
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -rm -r /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>&1',
    timeout=20
)
print(o.read().decode().strip()[:200])
time.sleep(2)

# 4. Check free memory
_, o, _ = c.exec_command('free -h | head -2', timeout=5)
print("\nMemory:", o.read().decode().strip())

# 5. Verify no Spark processes
_, o, _ = c.exec_command('ps aux | grep -E "spark|flask" | grep -v grep | wc -l', timeout=5)
print(f"Spark/Flask processes: {o.read().decode().strip()}")

# 6. Launch ORC conversion with ALL resources
print("\nLaunching ORC conversion (dedicated, no Flask)...")
cmd = (
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
    'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
    'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
    'export SPARK_HOME=/opt/spark-3.5.3 && '
    'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
    'cd /home/arafat && '
    'nohup /opt/spark-3.5.3/bin/spark-submit --master yarn --deploy-mode client '
    '--driver-memory 1g --executor-memory 3g --num-executors 1 --executor-cores 2 '
    '--conf spark.yarn.executor.memoryOverhead=512m '
    '--conf spark.network.timeout=800s '
    '--conf spark.executor.heartbeatInterval=200s '
    '--conf spark.task.maxFailures=8 '
    'optimize_orc.py > /home/arafat/orc_optimize.log 2>&1 &'
)
c.exec_command(cmd, timeout=5)
print("ORC job launched! Waiting 30s for init...")
time.sleep(30)

_, o, _ = c.exec_command('tail -5 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print(f"Log:\n{o.read().decode().strip()[:500]}")

c.close()
print("\nORC conversion running. It needs ~2 hours. DO NOT start Flask until done.")

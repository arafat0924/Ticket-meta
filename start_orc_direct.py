import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# Check if spark is already running
_, o, _ = c.exec_command('ps aux | grep "spark-submit" | grep -v grep', timeout=10)
spark_procs = o.read().decode().strip()
print(f"Spark-submit running: {'YES' if spark_procs else 'NO'}")
if spark_procs:
    print(spark_procs[:200])

if not spark_procs:
    # Clear old log and start fresh
    cmd = (
        'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && '
        'export HADOOP_HOME=/opt/hadoop-3.3.6 && '
        'export HADOOP_CONF_DIR=/opt/hadoop-3.3.6/etc/hadoop && '
        'export SPARK_HOME=/opt/spark-3.5.3 && '
        'export HIVE_HOME=/opt/apache-hive-4.0.1 && '
        'export PATH=$SPARK_HOME/bin:$HADOOP_HOME/bin:$PATH && '
        'cd /home/arafat && '
        'nohup spark-submit --master yarn --deploy-mode client '
        '--driver-memory 1g --executor-memory 2g --num-executors 1 --executor-cores 2 '
        'optimize_orc.py > /home/arafat/orc_optimize.log 2>&1 &'
    )
    c.exec_command(cmd, timeout=10)
    print("Started ORC conversion!")
    time.sleep(10)
    
    _, o, _ = c.exec_command('ps aux | grep "spark-submit" | grep -v grep | wc -l', timeout=10)
    print(f"Spark processes now: {o.read().decode().strip()}")
    
    _, o, _ = c.exec_command('cat /home/arafat/orc_optimize.log 2>/dev/null | head -5', timeout=10)
    print("Log start:", o.read().decode().strip()[:300])

c.close()

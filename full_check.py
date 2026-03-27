import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# Check if spark-submit is still running
_, o, _ = c.exec_command('ps aux | grep spark | grep -v grep | wc -l', timeout=10)
print("Spark processes:", o.read().decode().strip())

# Check log tail (last 20 lines)
_, o, _ = c.exec_command('tail -20 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Last 20 lines:")
print(o.read().decode().strip()[:1500])

# Check if ORC table exists on HDFS
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; /opt/hadoop-3.3.6/bin/hdfs dfs -du -s -h /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>/dev/null', timeout=15)
orc = o.read().decode().strip()
print(f"\nORC on HDFS: {orc if orc else '(not found)'}")

# Check total log lines  
_, o, _ = c.exec_command('wc -l /home/arafat/orc_optimize.log', timeout=10)
print("Total log lines:", o.read().decode().strip())

# Check if COMPLETE appears in log
_, o, _ = c.exec_command('grep -i "COMPLETE\|ERROR\|Exception\|FAIL\|Done\|stopped" /home/arafat/orc_optimize.log | tail -5', timeout=10)
result = o.read().decode().strip()
print(f"Status keywords: {result if result else '(none found)'}")

c.close()

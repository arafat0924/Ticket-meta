import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# Check for success/error in log
_, o, _ = c.exec_command('grep -i "COMPLETE\|ERROR\|Exception\|FAIL\|Done\|error\|Total time\|ORC test" /home/arafat/orc_optimize.log | tail -15', timeout=10)
print("Status:", o.read().decode().strip()[:800])

# Check our script output lines
_, o, _ = c.exec_command('grep "\\[" /home/arafat/orc_optimize.log | head -10', timeout=10)
print("\nScript output:", o.read().decode().strip()[:500])

# Check if ORC exists on HDFS
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -du -s -h /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>/dev/null',
    timeout=15
)
orc = o.read().decode().strip()
print(f"\nORC on HDFS: {orc if orc else '(not found)'}")

# List ORC partitions
_, o, _ = c.exec_command(
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; '
    '/opt/hadoop-3.3.6/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/itineraries_orc/ 2>/dev/null | head -10',
    timeout=15
)
print("\nORC partitions:", o.read().decode().strip()[:500])

c.close()

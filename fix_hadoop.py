import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# Kill the failing spark-submit first
c.exec_command('pkill -f spark-submit', timeout=10)
time.sleep(2)
print("Killed old spark-submit")

# Start YARN ResourceManager and NodeManager
cmds = [
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && export HADOOP_HOME=/opt/hadoop-3.3.6 && $HADOOP_HOME/sbin/start-yarn.sh',
    'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 && export HADOOP_HOME=/opt/hadoop-3.3.6 && $HADOOP_HOME/sbin/start-dfs.sh',
]

for cmd in cmds:
    _, o, e = c.exec_command(cmd, timeout=30)
    print(o.read().decode().strip()[:200])
    print(e.read().decode().strip()[:200])
    print("---")

time.sleep(5)

# Check jps
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; jps', timeout=10)
print("JPS:", o.read().decode().strip())

# Check YARN
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; /opt/hadoop-3.3.6/bin/yarn node -list 2>&1 | head -5', timeout=15)
print("YARN:", o.read().decode().strip()[:300])

c.close()

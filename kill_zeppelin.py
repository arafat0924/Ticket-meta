import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# Kill Zeppelin's Spark interpreter process
_, o, _ = c.exec_command('pkill -f "zeppelin.*spark-interpreter"; sleep 2; echo "Killed Zeppelin Spark"', timeout=15)
print(o.read().decode().strip())

# Also kill the YARN application for Zeppelin
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; /opt/hadoop-3.3.6/bin/yarn application -kill application_1774592551613_0002 2>/dev/null; echo done', timeout=30)
print("YARN kill:", o.read().decode().strip()[:300])

# Check current ORC progress
_, o, _ = c.exec_command('tail -5 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("ORC progress:", o.read().decode().strip()[:500])

c.close()
print("Done - more resources should be available now")

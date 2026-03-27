import paramiko, time, hashlib

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# 1. Upload both files
sftp = c.open_sftp()
sftp.put('d:/Internship/web/flask_api.py', '/home/arafat/flask_api.py')
print("Uploaded flask_api.py")
sftp.put('d:/Internship/web/optimize_orc.py', '/home/arafat/optimize_orc.py')
print("Uploaded optimize_orc.py")

# 2. Verify flask_api.py matches
with open('d:/Internship/web/flask_api.py', 'rb') as f:
    local_md5 = hashlib.md5(f.read()).hexdigest()
with sftp.open('/home/arafat/flask_api.py', 'rb') as f:
    vm_md5 = hashlib.md5(f.read()).hexdigest()
print(f"flask_api.py match: {local_md5 == vm_md5} (local={local_md5[:8]}, vm={vm_md5[:8]})")
sftp.close()

# 3. Start ORC optimization in background
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
print("Started ORC optimization in background")

time.sleep(8)

# 4. Check it started
_, o, _ = c.exec_command('head -5 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("Log:", o.read().decode().strip()[:500])

c.close()
print("Done!")

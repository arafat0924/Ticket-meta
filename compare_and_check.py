import paramiko, hashlib

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# 1. Compare flask_api.py
sftp = c.open_sftp()
try:
    with sftp.open('/home/arafat/flask_api.py', 'r') as f:
        vm_content = f.read()
    print(f"VM flask_api.py: {len(vm_content)} bytes, md5={hashlib.md5(vm_content).hexdigest()}")
except Exception as e:
    print(f"VM flask_api.py error: {e}")
    vm_content = b''

with open('d:/Internship/web/flask_api.py', 'rb') as f:
    local_content = f.read()
print(f"Local flask_api.py: {len(local_content)} bytes, md5={hashlib.md5(local_content).hexdigest()}")

if vm_content == local_content:
    print("MATCH: Files are identical!")
else:
    print("DIFFERENT: Files differ!")
    print(f"  VM size: {len(vm_content)} bytes")
    print(f"  Local size: {len(local_content)} bytes")
sftp.close()

# 2. Check running processes
_, o, _ = c.exec_command('ps aux | grep -E "flask_api|spark|optimize" | grep -v grep', timeout=10)
procs = o.read().decode().strip()
print(f"\nRunning processes:\n{procs if procs else '(none)'}")

# 3. Check if itineraries_orc exists in Hive
_, o, _ = c.exec_command('export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64; /opt/hadoop-3.3.6/bin/hdfs dfs -ls /user/hive/warehouse/ticketmeta09.db/itineraries_orc 2>/dev/null', timeout=15)
orc = o.read().decode().strip()
print(f"\nORC table on HDFS:\n{orc if orc else '(does not exist)'}")

c.close()

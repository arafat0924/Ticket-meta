import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

# Check if spark-submit is running
_, o, _ = c.exec_command('ps aux --no-headers -C java 2>/dev/null | wc -l', timeout=15)
print("Java processes:", o.read().decode().strip())

# Check log
_, o, _ = c.exec_command('tail -15 /home/arafat/orc_optimize.log 2>/dev/null', timeout=15)
log = o.read().decode().strip()
print("ORC Log:\n", log[:2000] if log else "(empty)")

# Check line count
_, o, _ = c.exec_command('wc -l /home/arafat/orc_optimize.log 2>/dev/null', timeout=15)
print("Log lines:", o.read().decode().strip())

c.close()

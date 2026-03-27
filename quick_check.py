import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=120)

# Check spark processes
_, o, _ = c.exec_command('ps aux | grep spark | grep -v grep | head -5', timeout=10)
print("Spark:", o.read().decode().strip()[:400])

# Check log
_, o, _ = c.exec_command('wc -l /home/arafat/orc_optimize.log 2>/dev/null; echo "---"; tail -5 /home/arafat/orc_optimize.log 2>/dev/null', timeout=10)
print("\nLog:", o.read().decode().strip()[:500])

# Check nohup.out for errors
_, o, _ = c.exec_command('cat /home/arafat/nohup.out 2>/dev/null | tail -5', timeout=10)
print("\nnohup.out:", o.read().decode().strip()[:300])

c.close()

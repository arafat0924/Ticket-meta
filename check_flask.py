import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

_, o, _ = c.exec_command('ps aux | grep flask_api | grep -v grep', timeout=10)
print("Processes:", o.read().decode().strip()[:300])

_, o, _ = c.exec_command('cat /home/arafat/flask_api.log 2>/dev/null | tail -20', timeout=10)
print("\nLog:", o.read().decode().strip()[:800])

_, o, _ = c.exec_command('curl -s http://localhost:5000/api/health 2>&1 | head -5', timeout=15)
print("\nHealth:", o.read().decode().strip()[:200])

c.close()

import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.56.104', username='arafat', password='092424', timeout=60)

_, o, _ = c.exec_command('ss -tlnp | grep 5000', timeout=10)
print("Port 5000:", o.read().decode().strip() or "(not listening)")

_, o, _ = c.exec_command('tail -3 /home/arafat/flask_api.log 2>/dev/null', timeout=10)
print("Log:", o.read().decode().strip()[:300])

c.close()

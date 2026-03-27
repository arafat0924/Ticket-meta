import paramiko, time
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.56.104", username="arafat", password="092424", timeout=60)

# Upload
sftp = c.open_sftp()
sftp.put("d:/Internship/web/flask_api.py", "/home/arafat/flask_api.py")
sftp.close()
print("✅ Uploaded flask_api.py")

# Fire-and-forget kill + restart (don't wait for output)
chan = c.get_transport().open_session(timeout=10)
chan.exec_command("pkill -9 -f flask_api; pkill -9 -f SparkSubmit; sleep 3; cd /home/arafat && nohup python3 flask_api.py > api.log 2>&1 &")
time.sleep(5)
print("✅ Restart command sent")

# Quick check
_, o, _ = c.exec_command("ps aux | grep flask_api | grep -v grep | head -1", timeout=10)
out = o.read().decode().strip()
print(f"Process: {out[:200]}" if out else "⏳ Starting...")

c.close()
print("\n🎉 Deployed! Wait ~3 min for Spark init, then test.")

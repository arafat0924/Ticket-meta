import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.56.104", username="arafat", password="092424", timeout=60)

def ssh(cmd, t=30):
    print(f"$ {cmd}")
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(f"  {out[:600]}")
    if err and "warning" not in err.lower() and "deprecat" not in err.lower() and "WARN" not in err:
        print(f"  ERR: {err[:300]}")
    return out

# Find Hadoop
print("=== Finding Hadoop ===")
ssh("ls /opt/ | grep -i hadoop", t=10)
ssh("ls /opt/hadoop-*/sbin/start-dfs.sh 2>/dev/null || echo 'Not in /opt/hadoop-*'", t=10)

# Check env
ssh("cat /etc/environment 2>/dev/null | head -10", t=10)

# Check azmine user's setup (original user)
ssh("ls /home/azmine/ 2>/dev/null | head -10", t=10)
ssh("grep -i HADOOP /home/azmine/.bashrc 2>/dev/null | head -5", t=10)
ssh("grep -i HADOOP /home/arafat/.bashrc 2>/dev/null | head -5", t=10)

# Check systemd services
ssh("systemctl list-units --type=service | grep -i -E 'hadoop|hdfs|yarn|hive' 2>/dev/null", t=10)

# Try common paths
for path in ["/opt/hadoop-3.3.6", "/opt/hadoop-3.4.0", "/usr/local/hadoop", "/home/arafat/hadoop", "/opt/hadoop"]:
    out = ssh(f"ls {path}/sbin/start-dfs.sh 2>/dev/null && echo 'FOUND: {path}'", t=5)
    if "FOUND" in out:
        print(f"\n*** Hadoop found at: {path} ***")
        break

c.close()

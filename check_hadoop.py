import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.56.104", username="arafat", password="092424", timeout=30)

def ssh(cmd, t=10):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode().strip()
    if out: print(out)
    return out

print("=== /opt contents ===")
ssh("ls /opt/")
print("\n=== bashrc ===")
ssh("cat /home/arafat/.bashrc | grep -i export | head -15")
print("\n=== hadoop check ===")
ssh("ls -la /opt/hadoop-3.3.6/sbin/start-dfs.sh 2>/dev/null; ls -la /opt/hadoop-3.4.0/sbin/start-dfs.sh 2>/dev/null; ls /opt/hadoop*/sbin/ 2>/dev/null | head -5")
print("\n=== source bashrc and check ===")
ssh("source /home/arafat/.bashrc 2>/dev/null; echo HADOOP_HOME=$HADOOP_HOME; echo SPARK_HOME=$SPARK_HOME; echo JAVA_HOME=$JAVA_HOME")

c.close()

const { Client } = require('ssh2');
const conn = new Client();

const commands = [
  // Check all Java processes across all nodes
  'jps 2>/dev/null',
  // Check HDFS status
  'export HADOOP_HOME=/opt/hadoop && $HADOOP_HOME/bin/hdfs dfsadmin -report 2>&1 | head -20',
  // Check YARN nodes
  'export HADOOP_HOME=/opt/hadoop && $HADOOP_HOME/bin/yarn node -list 2>&1 | head -10',
  // Check full API log for errors
  'tail -100 /home/azmine/flight_api/api.log 2>/dev/null',
  // Check if DataNode is running on workers
  'ssh node-worker-1 jps 2>/dev/null; ssh node-worker-2 jps 2>/dev/null',
  // Start HDFS and YARN if needed
  'export HADOOP_HOME=/opt/hadoop && $HADOOP_HOME/sbin/start-dfs.sh 2>&1 && $HADOOP_HOME/sbin/start-yarn.sh 2>&1',
];

let i = 0;
function runNext() {
  if (i >= commands.length) { conn.end(); return; }
  const cmd = commands[i];
  console.log(`\n===== [${i+1}] ${cmd.substring(0, 80)} =====`);
  conn.exec(cmd, { timeout: 30000 }, (err, stream) => {
    if (err) { console.error(err); i++; runNext(); return; }
    let out = '';
    stream.on('data', (d) => out += d.toString());
    stream.stderr.on('data', (d) => out += '[stderr] ' + d.toString());
    stream.on('close', () => { console.log(out.trim().substring(0, 2000)); i++; runNext(); });
  });
}

conn.on('ready', () => { console.log('Connected!'); runNext(); });
conn.on('error', (err) => console.error('Error:', err.message));
conn.connect({ host: 'node-master', port: 22, username: 'azmine', password: 'Ubuntu71$', readyTimeout: 30000 });

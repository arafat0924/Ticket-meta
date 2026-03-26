const { Client } = require('ssh2');

const conn = new Client();
const commands = [
  'curl -s --max-time 5 http://localhost:5000/api/health 2>/dev/null || echo "NOT_RUNNING"',
  'pkill -9 -f flask_api 2>/dev/null; pkill -9 -f SkyQuery 2>/dev/null; sleep 2',
  'rm -rf /tmp/blockmgr-* /tmp/spark-* 2>/dev/null',
  `cat > /tmp/start_api.sh << 'SCRIPT'
#!/bin/bash
export SPARK_HOME=/opt/spark-3.5.3
export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip
export HIVE_METASTORE_URIS=""
export SPARK_MASTER="local[*]"
cd /home/azmine/flight_api
truncate -s 0 api.log
nohup python3 flask_api.py > api.log 2>&1 &
echo "PID=$!"
sleep 3
kill -0 $! && echo "RUNNING" || echo "FAILED"
SCRIPT`,
  'bash /tmp/start_api.sh',
];

let cmdIndex = 0;

function runNext() {
  if (cmdIndex >= commands.length) {
    console.log('\n✅ All commands executed. Waiting 60s for Spark init...');
    setTimeout(() => {
      conn.exec('curl -s --max-time 15 http://localhost:5000/api/health', (err, stream) => {
        if (err) { console.error(err); conn.end(); return; }
        let out = '';
        stream.on('data', (d) => out += d.toString());
        stream.on('close', () => {
          console.log('Health check:', out);
          if (out.includes('"connected"')) {
            console.log('\n✅ Backend is UP and connected!');
          } else {
            console.log('\n⏳ Still warming up. Give it another 30-60s.');
          }
          conn.end();
        });
      });
    }, 60000);
    return;
  }

  const cmd = commands[cmdIndex];
  console.log(`\n$ ${cmd.substring(0, 80)}${cmd.length > 80 ? '...' : ''}`);
  
  conn.exec(cmd, (err, stream) => {
    if (err) { console.error('Error:', err); cmdIndex++; runNext(); return; }
    let out = '';
    stream.on('data', (d) => { out += d.toString(); });
    stream.stderr.on('data', (d) => { /* ignore warnings */ });
    stream.on('close', () => {
      if (out.trim()) console.log('  ', out.trim().substring(0, 500));
      cmdIndex++;
      runNext();
    });
  });
}

conn.on('ready', () => {
  console.log('Connected to node-master!');
  runNext();
});

conn.on('error', (err) => {
  console.error('Connection error:', err.message);
});

conn.connect({
  host: 'node-master',
  port: 22,
  username: 'azmine',
  password: 'Ubuntu71$',
  readyTimeout: 30000,
});

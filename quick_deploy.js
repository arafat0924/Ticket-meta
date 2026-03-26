const {Client} = require('ssh2');
const fs = require('fs');
const path = require('path');

const conn = new Client();
const localFile = path.join(__dirname, 'flask_api.py');
const remoteFile = '/home/azmine/flight_api/flask_api.py';

console.log('Connecting to VM...');
conn.on('ready', () => {
  console.log('Connected! Uploading flask_api.py...');
  conn.sftp((err, sftp) => {
    if (err) { console.error('SFTP error:', err); conn.end(); return; }
    const content = fs.readFileSync(localFile);
    sftp.writeFile(remoteFile, content, (err) => {
      if (err) { console.error('Upload error:', err); conn.end(); return; }
      console.log('Upload complete!');
      
      // Clear the backend cache so old weather data is refreshed
      console.log('Clearing backend cache...');
      conn.exec('curl -s --max-time 10 http://localhost:5000/api/cache/clear', (err, stream) => {
        if (err) { console.error('Exec error:', err); conn.end(); return; }
        let output = '';
        stream.on('data', (d) => { output += d.toString(); });
        stream.on('close', () => {
          console.log('Cache clear response:', output || '(no response - API may need restart)');
          
          // Kill and restart the API
          console.log('Restarting Flask API...');
          const restartCmd = `pkill -9 -f flask_api 2>/dev/null; sleep 2; ` +
            `export SPARK_HOME=/opt/spark-3.5.3 && ` +
            `export SPARK_CONF_DIR=/home/azmine/flight_api/spark-conf && ` +
            `export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop && ` +
            `export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip && ` +
            `cd /home/azmine/flight_api && ` +
            `nohup python3 flask_api.py > api.log 2>&1 & ` +
            `echo "API restarted with PID $!"`;
          
          conn.exec(restartCmd, (err, stream2) => {
            if (err) { console.error('Restart error:', err); conn.end(); return; }
            let out2 = '';
            stream2.on('data', (d) => { out2 += d.toString(); });
            stream2.on('close', () => {
              console.log(out2);
              console.log('Done! API will take ~90s to initialize Spark.');
              conn.end();
            });
          });
        });
      });
    });
  });
}).on('error', (err) => {
  console.error('Connection error:', err.message);
}).connect({
  host: 'node-master',
  port: 22,
  username: 'azmine',
  password: 'Ubuntu71$'
});

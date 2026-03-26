const { Client } = require('ssh2');
const conn = new Client();

const commands = [
  'ps aux | grep flask_api | grep -v grep',
  'tail -50 /home/azmine/flight_api/api.log 2>/dev/null',
  'curl -s --max-time 30 http://localhost:5000/api/health 2>&1',
  'jps 2>/dev/null | grep -v Jps',
];

let i = 0;
function runNext() {
  if (i >= commands.length) { conn.end(); return; }
  const cmd = commands[i];
  console.log(`\n===== ${cmd} =====`);
  conn.exec(cmd, { timeout: 35000 }, (err, stream) => {
    if (err) { console.error(err); i++; runNext(); return; }
    let out = '';
    stream.on('data', (d) => out += d.toString());
    stream.stderr.on('data', (d) => out += d.toString());
    stream.on('close', () => { console.log(out.trim().substring(0, 3000)); i++; runNext(); });
  });
}

conn.on('ready', () => { console.log('Connected!'); runNext(); });
conn.on('error', (err) => console.error('Error:', err.message));
conn.connect({ host: 'node-master', port: 22, username: 'azmine', password: 'Ubuntu71$', readyTimeout: 30000 });

// Writes config.json from environment variables, then starts `next start`.
const fs = require('fs');
const { spawn } = require('child_process');

const publicUrl = (process.env.PUBLIC_URL || '').replace(/\/+$/, '');
if (!publicUrl) {
  console.error('PUBLIC_URL is required');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync('/app/config.json', 'utf8'));
config.serverRuntimeConfig.backend.csrfKey = process.env.CSRF_KEY || config.serverRuntimeConfig.backend.csrfKey;
config.publicRuntimeConfig.backend.baseUrl = publicUrl;
// Every "{0}.roblox.com" API host is served by the website itself under /apisite/<name>.
config.publicRuntimeConfig.backend.apiFormat = publicUrl + '/apisite/{0}{1}';
fs.writeFileSync('/app/config.json', JSON.stringify(config));

const child = spawn('npx', ['next', 'start', '-p', '3000'], { stdio: 'inherit', cwd: '/app' });
child.on('exit', (code) => process.exit(code ?? 1));

import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [url, output, mode = 'page'] = process.argv.slice(2);
const profile = path.resolve('tmp', `chrome-${Date.now()}`);
await mkdir(profile, { recursive: true });
const browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
let socket;
try {
  let port;
  for (let i = 0; i < 100; i++) {
    try { port = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; break; }
    catch { await new Promise(resolve => setTimeout(resolve, 200)); }
  }
  if (!port) throw new Error('Chrome did not start');
  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })).json();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error))); else resolve(message.result);
    }
  };
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params }));
  });
  await call('Page.enable');
  await call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await call('Page.navigate', { url });
  for (let i = 0; i < 100; i++) {
    const state = await call('Runtime.evaluate', { expression: 'document.readyState === "complete" && !!document.querySelector("h1")' });
    if (state.result.value === true) break;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  await new Promise(resolve => setTimeout(resolve, 1500));
  if (mode === 'sql') {
    const clicked = await call('Runtime.evaluate', { expression: `(() => {
      const root = document.querySelector('#djDebugRoot');
      const scope = root.shadowRoot || root;
      const button = scope.querySelector('a.SQLPanel');
      if (!button) throw new Error('SQL panel button missing');
      button.click(); return true;
    })()` });
    if (clicked.exceptionDetails) throw new Error(JSON.stringify(clicked.exceptionDetails));
    await new Promise(resolve => setTimeout(resolve, 800));
  }
  const image = await call('Page.captureScreenshot', { format: 'png' });
  await writeFile(output, Buffer.from(image.data, 'base64'));
  console.log(`Screenshot: ${output}`);
  await call('Browser.close');
} finally {
  if (socket) socket.close();
  browser.kill();
}


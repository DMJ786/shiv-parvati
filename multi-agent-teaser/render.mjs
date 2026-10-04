import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
const [,, mode='video', arg1='', arg2=''] = process.argv;
const FPS = +(process.env.FPS || 30), DUR = 45;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--force-color-profile=srgb','--font-render-hinting=none'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('PAGEERR', e.message));
page.on('console', m => { if (m.type()==='error') console.error('CONSOLE', m.text()); });
await page.goto('file://' + process.cwd() + '/index.html');
await page.evaluate(() => window.ready);
if (mode === 'stills') {
  for (const t of arg1.split(',').map(Number)) {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: `${arg2}/f_${String(t.toFixed(2)).padStart(6,'0')}.png` });
  }
} else {
  const out = arg1 || 'silent.mp4';
  const ff = spawn('ffmpeg', ['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','slow','-crf','20','-maxrate','16M','-bufsize','32M','-pix_fmt','yuv420p','-movflags','+faststart',out], { stdio: ['pipe','inherit','inherit'] });
  const n = Math.round(DUR * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close();

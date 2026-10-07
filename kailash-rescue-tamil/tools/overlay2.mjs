import { chromium } from 'playwright-core';
const [html, out, id, inner] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.goto('file://' + html + '?id=' + id + '&h=' + encodeURIComponent(inner)); await p.evaluate(() => document.fonts.ready);
await p.screenshot({ path: out, omitBackground: true }); await b.close();

import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await p.goto('file://' + process.argv[2]); await p.evaluate(() => document.fonts.ready);
await p.screenshot({ path: process.argv[3], omitBackground: true }); await b.close();

// Minimal local RSSHub: turns any RSSHub route into RSS on http://localhost:1200<route>,
// using the official npm package (init + request), for testing Dawnbrief without Docker.
import http from 'node:http';

// Without a fixed user agent, every route failed on Windows with "No headers based on this input can be
// generated" (RSSHub's header generator). Set it before RSSHub loads, so import it dynamically.
process.env.UA ??= 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36';
const { init, request } = await import('rsshub');

await init({});
const esc = (s = '') => String(s).replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' })[c]);

http.createServer(async (req, res) => {
  try {
    const data = await request(req.url);
    const items = (data.item || []).map((i) =>
      `<item><title>${esc(i.title)}</title><link>${esc(i.link)}</link>` +
      (i.pubDate ? `<pubDate>${new Date(i.pubDate).toUTCString()}</pubDate>` : '') + '</item>').join('');
    res.writeHead(200, { 'Content-Type': 'application/rss+xml; charset=utf-8' });
    res.end(`<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>${esc(data.title)}</title>${items}</channel></rss>`);
    console.log(`200 ${req.url} (${(data.item || []).length} items)`);
  } catch (e) {
    res.writeHead(502);
    res.end(String(e));
    console.log(`502 ${req.url} ${e}`);
  }
}).listen(1200, '127.0.0.1', () => console.log('RSSHub (npm) on http://localhost:1200'));

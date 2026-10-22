import assert from "node:assert/strict";
process.env.DATA_DIR = `${process.env.TMPDIR ?? "/tmp"}/savia-smoke-${Date.now()}`;
const { addProduct, getOrCreateShop, updateShop } = await import("./db.js");
const { generateProduct } = await import("./ai.js");
const { createServer, esc } = await import("./server.js");

const shop = getOrCreateShop(1, "Test Shop");
updateShop(shop.id, { contact: "@tester" });
const g = await generateProduct({ text: "qizil ko'ylak 180000 so'm" });
const p = addProduct({ shop_id: shop.id, category: g.category, price: g.price, currency: g.currency, attributes: g.attributes, translations: g.translations, photos: [] });
assert.equal(p.price, 180000);

const srv = createServer().listen(0);
const base = `http://localhost:${(srv.address() as any).port}`;
const cat = await (await fetch(`${base}/s/${shop.slug}?lang=ru`)).text();
assert.match(cat, /qizil/);
const prod = await (await fetch(`${base}/s/${shop.slug}/p/${p.id}`)).text();
assert.match(prod, /t\.me\/tester/);
const chat = await (await fetch(`${base}/api/chat`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ productId: p.id, lang: "uz", question: "razmeri bormi?" }) })).json();
assert.ok(chat.answer);
assert.equal((await fetch(`${base}/s/nope`)).status, 404);
assert.equal(esc(`<script>"'`), "&lt;script&gt;&quot;&#39;");
srv.close();
console.log("smoke ok");

import express from "express";
import { DATA_DIR, LANGS, getProduct, getShopById, getShopBySlug, listProducts, logQuestion } from "./db.js";
import type { Lang, Product, Shop } from "./db.js";
import { answerQuestion } from "./ai.js";

const UI: Record<Lang, Record<string, string>> = {
  uz: { ask: "Savol bering", send: "Yuborish", contact: "Sotuvchiga yozish", empty: "Hozircha mahsulot yo'q", hint: "Masalan: razmeri bormi?", back: "Katalog", price: "Narxi", agree: "Narxi kelishiladi" },
  ru: { ask: "Задайте вопрос", send: "Отправить", contact: "Написать продавцу", empty: "Товаров пока нет", hint: "Например: есть ли размер?", back: "Каталог", price: "Цена", agree: "Цена договорная" },
  en: { ask: "Ask a question", send: "Send", contact: "Message the seller", empty: "No products yet", hint: "e.g. is it available in size M?", back: "Catalog", price: "Price", agree: "Price on request" },
};

export const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

const asLang = (v: unknown): Lang => (LANGS.includes(v as Lang) ? (v as Lang) : "uz");

const priceText = (p: Product, l: Lang) =>
  p.price == null ? UI[l].agree : `${new Intl.NumberFormat("ru-RU").format(p.price)} ${p.currency}`;

const contactHref = (c: string) => {
  const v = c.trim();
  if (/^@\w+$/.test(v)) return `https://t.me/${v.slice(1)}`;
  if (/^\+?[\d\s()-]{7,}$/.test(v)) return `tel:${v.replace(/[^\d+]/g, "")}`;
  return /^https?:\/\//.test(v) ? v : "";
};

const page = (title: string, body: string) => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:#f6f6f7;color:#1a1a1a}
header{background:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #eee;position:sticky;top:0}
header a{color:inherit;text-decoration:none;font-weight:700}.langs a{margin-left:8px;font-weight:400;color:#666}
main{max-width:960px;margin:0 auto;padding:16px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.card{background:#fff;border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;display:block}
.card img,.ph{width:100%;aspect-ratio:1;object-fit:cover;background:#e8e8ea;display:block}.card div{padding:10px}
.price{font-weight:700;margin-top:4px}.detail{background:#fff;border-radius:12px;overflow:hidden}.detail .in{padding:16px}
.attrs{color:#555;font-size:14px}.btn{display:inline-block;background:#1a1a1a;color:#fff;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;cursor:pointer;font-size:15px}
#log{margin:12px 0;display:flex;flex-direction:column;gap:8px}.m{padding:8px 12px;border-radius:12px;max-width:85%}
.u{background:#1a1a1a;color:#fff;align-self:flex-end}.a{background:#eee}form{display:flex;gap:8px}input{flex:1;padding:10px;border:1px solid #ccc;border-radius:8px;font-size:15px}
</style></head><body>${body}</body></html>`;

const header = (shop: Shop, lang: Lang, path: string) =>
  `<header><a href="/s/${esc(shop.slug)}?lang=${lang}">${esc(shop.name)}</a>
<span class="langs">${LANGS.map((l) => `<a href="${path}?lang=${l}">${l.toUpperCase()}</a>`).join("")}</span></header>`;

export function createServer() {
  const app = express();
  app.use(express.json({ limit: "10kb" }));
  app.use("/photos", express.static(`${DATA_DIR}/photos`, { maxAge: "1d" }));

  app.get("/healthz", (_req, res) => void res.json({ ok: true }));

  app.get("/s/:slug", (req, res) => {
    const shop = getShopBySlug(req.params.slug);
    if (!shop) return void res.status(404).send("Not found");
    const lang = asLang(req.query.lang);
    const items = listProducts(shop.id);
    const cards = items
      .map((p) => {
        const t = p.translations[lang];
        const img = p.photo ? `<img loading="lazy" src="/photos/${esc(p.photo)}" alt="">` : `<div class="ph"></div>`;
        return `<a class="card" href="/s/${esc(shop.slug)}/p/${p.id}?lang=${lang}">${img}<div>${esc(t.title)}<div class="price">${esc(priceText(p, lang))}</div></div></a>`;
      })
      .join("");
    res.send(
      page(shop.name, `${header(shop, lang, `/s/${esc(shop.slug)}`)}<main>${items.length ? `<div class="grid">${cards}</div>` : `<p>${UI[lang].empty}</p>`}</main>`),
    );
  });

  app.get("/s/:slug/p/:id", (req, res) => {
    const shop = getShopBySlug(req.params.slug);
    const product = getProduct(Number(req.params.id));
    if (!shop || !product || product.shop_id !== shop.id) return void res.status(404).send("Not found");
    const lang = asLang(req.query.lang);
    const t = product.translations[lang];
    const ui = UI[lang];
    const attrs = Object.entries(product.attributes).map(([k, v]) => `${esc(k)}: ${esc(v)}`).join(" · ");
    const href = contactHref(shop.contact);
    const img = product.photo ? `<img src="/photos/${esc(product.photo)}" alt="">` : "";
    const body = `${header(shop, lang, `/s/${esc(shop.slug)}/p/${product.id}`)}<main>
<p><a href="/s/${esc(shop.slug)}?lang=${lang}">← ${ui.back}</a></p>
<div class="detail">${img}<div class="in"><h2>${esc(t.title)}</h2><div class="price">${esc(priceText(product, lang))}</div>
<p>${esc(t.description)}</p><p class="attrs">${attrs}</p>
${href ? `<p><a class="btn" href="${esc(href)}">${ui.contact}</a></p>` : ""}
<h3>${ui.ask}</h3><div id="log"></div>
<form id="f"><input id="q" maxlength="300" placeholder="${esc(ui.hint)}" required><button class="btn">${ui.send}</button></form></div></div></main>
<script>
const log=document.getElementById('log');
function add(c,t){const d=document.createElement('div');d.className='m '+c;d.textContent=t;log.appendChild(d)}
document.getElementById('f').onsubmit=async e=>{e.preventDefault();const q=document.getElementById('q');const text=q.value.trim();if(!text)return;
add('u',text);q.value='';
try{const r=await fetch('/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({productId:${product.id},lang:'${lang}',question:text})});
const j=await r.json();add('a',j.answer||'...')}catch{add('a','Error')}};
</script>`;
    res.send(page(`${t.title} — ${shop.name}`, body));
  });

  app.post("/api/chat", async (req, res) => {
    const { productId, lang, question } = req.body ?? {};
    const product = getProduct(Number(productId));
    const q = typeof question === "string" ? question.trim().slice(0, 300) : "";
    if (!product || !q) return void res.status(400).json({ error: "bad request" });
    const shop = getShopById(product.shop_id)!;
    try {
      const r = await answerQuestion(product, shop.name, asLang(lang), q);
      logQuestion(product.id, q, !r.needsSeller);
      if (r.needsSeller) notifySeller?.(shop, product, q);
      res.json({ answer: r.answer });
    } catch (e) {
      console.error("chat failed", e);
      res.status(502).json({ answer: "Hozir javob bera olmayman, keyinroq urinib ko'ring." });
    }
  });

  return app;
}

/** Set by the bot so unanswered buyer questions reach the seller. */
let notifySeller: ((shop: Shop, product: Product, question: string) => void) | undefined;
export const setSellerNotifier = (fn: typeof notifySeller) => void (notifySeller = fn);

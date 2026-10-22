import { Bot, InlineKeyboard } from "grammy";
import { writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { DATA_DIR, addProduct, deleteProduct, getOrCreateShop, getShopById, listProducts, updateShop } from "./db.js";
import { generateProduct } from "./ai.js";
import { setSellerNotifier } from "./server.js";

const PUBLIC_URL = (
  process.env.PUBLIC_URL ??
  (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : "http://localhost:3000")
).replace(/\/$/, "");
const MAX_PHOTO_BYTES = 8 * 1024 * 1024;

export function createBot(token: string) {
  const bot = new Bot(token);
  const shopOf = (ctx: { from?: { id: number; first_name: string } }) =>
    getOrCreateShop(ctx.from!.id, ctx.from!.first_name);
  const link = (slug: string) => `${PUBLIC_URL}/s/${slug}`;

  bot.command("start", async (ctx) => {
    const shop = shopOf(ctx);
    await ctx.reply(
      `Salom! Men Savia botman.\n\nMahsulot qo'shish: rasm yuboring va izohga yozing, masalan:\n"qizil ko'ylak, 42-razmer, 180000 so'm"\n\nAI tavsif yozadi va o'zbek/rus/ingliz tillariga tarjima qiladi.\n\nDo'koningiz: ${link(shop.slug)}\n\nBuyruqlar:\n/products — mahsulotlar\n/name Do'kon nomi\n/contact @username yoki +998...\n/shop — do'kon linki`,
    );
  });

  bot.command("shop", (ctx) => ctx.reply(link(shopOf(ctx).slug)));

  bot.command("name", async (ctx) => {
    const name = ctx.match.trim().slice(0, 60);
    if (!name) return void ctx.reply("Masalan: /name Gulnora Moda");
    updateShop(shopOf(ctx).id, { name });
    await ctx.reply("Do'kon nomi yangilandi.");
  });

  bot.command("contact", async (ctx) => {
    const contact = ctx.match.trim().slice(0, 80);
    if (!contact) return void ctx.reply("Masalan: /contact @gulnora yoki /contact +998901234567");
    updateShop(shopOf(ctx).id, { contact });
    await ctx.reply("Aloqa ma'lumoti saqlandi.");
  });

  bot.command("products", async (ctx) => {
    const items = listProducts(shopOf(ctx).id);
    if (!items.length) return void ctx.reply("Hali mahsulot yo'q. Rasm yuboring.");
    for (const p of items.slice(0, 20)) {
      await ctx.reply(`#${p.id} ${p.translations.uz.title} — ${p.price ?? "?"} ${p.currency}`, {
        reply_markup: new InlineKeyboard().text("O'chirish", `del:${p.id}`),
      });
    }
  });

  bot.callbackQuery(/^del:(\d+)$/, async (ctx) => {
    const ok = deleteProduct(Number(ctx.match[1]), shopOf(ctx).id);
    await ctx.answerCallbackQuery(ok ? "O'chirildi" : "Topilmadi");
    if (ok) await ctx.editMessageText("O'chirildi.");
  });

  type Img = { id: string; mime: string };
  const MEDIA = ["image/jpeg", "image/png", "image/webp", "image/gif"] as const;
  const MAX_IMAGES = 6;
  const MAX_AI_IMAGES = 4;

  async function createFromMessage(ctx: any, text: string, files: Img[]) {
    const shop = shopOf(ctx);
    await ctx.replyWithChatAction("typing");
    const photos: string[] = [];
    const images: NonNullable<Parameters<typeof generateProduct>[0]["images"]> = [];
    for (const f of files.slice(0, MAX_IMAGES)) {
      const file = await ctx.api.getFile(f.id);
      const res = await fetch(`https://api.telegram.org/file/bot${token}/${file.file_path}`);
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length > MAX_PHOTO_BYTES) continue;
      const mediaType = (MEDIA as readonly string[]).includes(f.mime) ? (f.mime as (typeof MEDIA)[number]) : "image/jpeg";
      const name = `${randomUUID()}.${mediaType.split("/")[1]}`;
      writeFileSync(`${DATA_DIR}/photos/${name}`, buf);
      photos.push(name);
      if (images.length < MAX_AI_IMAGES) images.push({ base64: buf.toString("base64"), mediaType });
    }
    try {
      const g = await generateProduct({ text, images });
      const p = addProduct({ shop_id: shop.id, category: g.category, price: g.price, currency: g.currency || "UZS", attributes: g.attributes ?? {}, translations: g.translations, photos });
      const uz = p.translations.uz;
      await ctx.reply(
        `Qo'shildi (#${p.id}, ${photos.length} ta rasm):\n\n${uz.title}\n${uz.description}\nNarxi: ${p.price ?? "ko'rsatilmagan"} ${p.currency}\n\nKatalog: ${link(shop.slug)}`,
        { reply_markup: new InlineKeyboard().text("O'chirish", `del:${p.id}`) },
      );
    } catch (e) {
      console.error("product generation failed", e);
      await ctx.reply("AI xatolik berdi, qayta urinib ko'ring.");
    }
  }

  // Telegram sends an album as separate messages sharing media_group_id; merge them into one product.
  const albums = new Map<string, { files: Img[]; caption: string; ctx: any; timer?: NodeJS.Timeout }>();
  function collect(ctx: any, file: Img) {
    const caption: string = ctx.message.caption ?? "";
    const gid: string | undefined = ctx.message.media_group_id;
    if (!gid) return createFromMessage(ctx, caption, [file]);
    let g = albums.get(gid);
    if (!g) albums.set(gid, (g = { files: [], caption: "", ctx }));
    g.files.push(file);
    if (caption) g.caption = caption;
    clearTimeout(g.timer);
    g.timer = setTimeout(() => {
      albums.delete(gid);
      void createFromMessage(g!.ctx, g!.caption, g!.files);
    }, 1500);
  }

  bot.on("message:photo", (ctx) => {
    const sizes = ctx.message.photo;
    return collect(ctx, { id: sizes[sizes.length - 1].file_id, mime: "image/jpeg" });
  });

  bot.on("message:document", (ctx) => {
    const d = ctx.message.document;
    if (!d.mime_type?.startsWith("image/")) return ctx.reply("Faqat rasm yuboring (jpg, png, webp).");
    return collect(ctx, { id: d.file_id, mime: d.mime_type });
  });

  bot.on("message:text", (ctx) => {
    if (ctx.message.text.startsWith("/")) return;
    return ctx.reply(
      "Mahsulot qo'shish uchun rasm yuboring va narx/tavsifni rasm izohiga (caption) yozing.\nMasalan: rasm + \"erkaklar kurtkasi, 500 000 so'm\".\nMahsulotlar: /products",
    );
  });

  bot.on("message:voice", (ctx) =>
    ctx.reply("Ovozli xabar keyingi versiyada. Hozircha matn yoki rasm+izoh yuboring."),
  );

  setSellerNotifier((shop, product, question) => {
    bot.api
      .sendMessage(shop.tg_id, `Xaridor savoli (${product.translations.uz.title}, #${product.id}):\n"${question}"\n\nAI javob bera olmadi, o'zingiz bog'laning.`)
      .catch((e) => console.error("notify failed", e));
  });

  bot.catch((e) => console.error("bot error", e.error));
  return bot;
}

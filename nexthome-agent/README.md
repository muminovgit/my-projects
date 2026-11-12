# Nexthome agent

[nexthome.uz](https://nexthome.uz) uchun Telegram bot-agent. Ikki ish qiladi:

1. **Telegram postini e'longa aylantiradi.** Kanaldagi postni (rasmlari bilan) botga forward qilasiz — Claude undan narx, xonalar, hudud, manzil va boshqa ma'lumotlarni ajratadi, qoralamani ko'rsatadi, "Joylash" bosilsa rasmlarni yuklab e'lonni saytga chiqaradi.
2. **Saytni boshqaradi va analitika beradi.** Botga oddiy so'z bilan yozasiz ("bu hafta nechta e'lon qo'shildi?", "kutayotgan e'lonlarni ko'rsat", "123-e'lonni tasdiqla") — agent Nexthome API orqali javob topadi yoki amalni bajaradi.

Bot Nexthome'ning o'z MCP serveri (`https://api.nexthome.uz/mcp`) orqali, siz bergan akkaunt huquqlari doirasida ishlaydi.

## Claude'ga ulash (botsiz ham ishlaydi)

Nexthome MCP serveri OAuth bilan himoyalangan, shuning uchun Claude'ga to'g'ridan-to'g'ri ulanadi:

- **Claude Code:** shu papkani oching — `.mcp.json` dagi `nexthome` serveri taklif qilinadi. `/mcp` buyrug'i orqali Nexthome akkauntingiz bilan kiring. `nexthome-post` skill'i va `CLAUDE.md` ham shu papkada.
- **claude.ai / Claude Desktop:** sozlamalardagi connectors bo'limida custom connector qo'shing, URL: `https://api.nexthome.uz/mcp`. Nexthome login oynasi ochiladi.

Shundan keyin Claude'ning o'zidan e'lonlar, moderatsiya, agentlik statistikasi va chatlarni boshqarish mumkin.

## Botni o'rnatish

Node.js 20+ kerak.

```bash
npm install
```

```bash
cp .env.example .env
```

`.env` ni to'ldiring:

| O'zgaruvchi | Qayerdan olinadi |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` |
| `ADMIN_IDS` | Botni ishga tushirib `/id` yozing; chiqqan raqamni qo'ying (bir nechta bo'lsa vergul bilan) |
| `NEXTHOME_MCP_TOKEN` | `npm run connect` (pastda) |
| `ANTHROPIC_API_KEY` | [platform.claude.com](https://platform.claude.com) → API keys |

Nexthome tokenini olish — telefon raqam va parol so'raladi, ular hech qayerga saqlanmaydi:

```bash
npm run connect
```

Ishga tushirish:

```bash
npm start
```

Yoki Docker bilan (serverda doimiy ishlashi uchun):

```bash
docker compose up -d --build
```

## Ishlatish

**E'lon joylash.** Kanal postini botga forward qiling (albom bo'lsa hammasi birga). Bot qoralamani ko'rsatadi:

- **Joylash** — rasmlar yuklanadi, e'lon yaratiladi va moderatsiyaga tushadi. Akkauntda moderator huquqi bo'lsa, shu yerning o'zida "Tasdiqlash / Rad etish" tugmalari chiqadi.
- **Tuzatish** — nimani o'zgartirishni bir xabarda yozasiz ("narxi 350 dollar, 3-qavat"), qoralama yangilanadi.
- **Bekor** — qoralama o'chiriladi.

Postdagi telefon raqam e'lon tavsifiga qo'shiladi. Bir xil post ikkinchi marta yuborilsa, bot ogohlantiradi.

**Kanaldan avtomatik olish (ixtiyoriy).** Botni kanalga admin qilib, kanal ID'sini `SOURCE_CHANNEL_IDS` ga yozing — har bir yangi post birinchi admin'ga qoralama bo'lib keladi. `AUTO_PUBLISH=true` qilinsa, narxi va hududi aniq postlar so'ramasdan joylanadi.

**Analitika va boshqaruv.** Oddiy xabar yozing. Ma'lumotni o'zgartiradigan har bir amal oldidan bot "Bajaraymi?" deb tugma ko'rsatadi — bosmaguningizcha hech narsa o'zgarmaydi. `/new` suhbatni tozalaydi.

Analitika Nexthome API bergan ma'lumotlardan hisoblanadi: e'lonlar soni va dinamikasi, narxlar, hududlar, moderatsiya navbati, shikoyatlar, agentlik ko'rsatkichlari (ko'rishlar, ko'rsatuvlar, konversiya). Butun sayt bo'yicha tashrif/trafik manbalari API'da yo'q — buning uchun saytga Yandex Metrika yoki Google Analytics ulanishi kerak.

## Xavfsizlik

- Botdan faqat `ADMIN_IDS` dagi foydalanuvchilar foydalana oladi.
- Bot Nexthome'da token berilgan akkaunt huquqlaridan tashqariga chiqa olmaydi; tokenni `npm run connect` da tanlangan muddat tugagach yangilash kerak.
- Parol, SMS-kod va ro'yxatdan o'tish bilan bog'liq API amallari agentdan yashirilgan.
- `.env` faylini hech kimga bermang va git'ga qo'shmang.

## Sinov

```bash
npm test
```

Soxta Telegram, Nexthome va Anthropic serverlari bilan to'liq oqimni tekshiradi (albom → qoralama → joylash, begona foydalanuvchini rad etish, tasdiqlash tugmasi). `LIVE=1 npm test` jonli Nexthome MCP serverining ochiq tool'larini ham tekshiradi.

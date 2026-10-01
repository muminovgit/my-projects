# Tour bot

Turlarni ko'rsatish, bron qilish va mijoz savollariga AI orqali javob berish uchun Telegram bot
(Python, aiogram 3, SQLAlchemy, Claude API). Bot: @maketour_bot

## Hozir nimalar bor

- `/start` → til tanlash (o'zbekcha / ruscha / inglizcha) → asosiy menyu
- **Turlar**: yo'nalish (O'zbekiston bo'ylab, Xorijga, Umra va Haj) → turlar ro'yxati → tur kartochkasi (narx, sana, bo'sh joylar), mijoz tilida
- **AI yordamchi**: mijoz istalgan savolni yozadi, AI turlar katalogi asosida javob beradi. Mijoz bron qilmoqchi bo'lsa yoki raqamini bersa, adminga **lead** boradi (kim, raqami, nima xohlaydi)
- To'lov bot ichida yo'q: menejer mijoz bilan o'zi bog'lanadi
- **Bron qilish**: necha kishi → telefon (tugma yoki qo'lda) → tasdiqlash
- Bron adminga **Tasdiqlash / Rad etish** tugmalari bilan boradi, mijozga natija xabari yuboriladi
- **Bronlarim**: mijozning bronlari va holati
- Admin: `/admin`, `/addtour` (qadamma-qadam tur qo'shish, AI ruscha va inglizchaga o'zi tarjima qiladi),
  `/aitour <qisqa tavsif>` (AI turni 3 tilda to'liq yozib beradi, admin "Saqlash" ni bosadi), `/cancel`
- Bo'sh joylar hisoblanadi: kutilayotgan va tasdiqlangan bronlar joy egallaydi, rad etilganlari bo'shatadi

## Ishga tushirish

```bash
cd tour-bot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # keyin .env ichiga BOT_TOKEN va ADMIN_IDS yozing
python -m bot
```

`BOT_TOKEN` ni @BotFather beradi. O'z Telegram ID'ingizni @userinfobot orqali bilib, `ADMIN_IDS` ga yozing.
`ANTHROPIC_API_KEY` ni console.anthropic.com dan olasiz. Kalit bo'lmasa bot ishlaydi, faqat AI o'chiq bo'ladi
va mijoz savollari to'g'ridan-to'g'ri adminga yuboriladi.
`.env` fayli git'ga tushmaydi, tokenni hech qayerga yubormang.

## Ma'lumotlar bazasi

Standart holatda `tour_bot.db` (SQLite) fayli avtomatik yaratiladi. Agar oldingi versiyani ishga tushirgan
bo'lsangiz, eski `tour_bot.db` ni o'chiring (jadvallar o'zgardi).
PostgreSQL'ga o'tish uchun `pip install asyncpg` qiling va `.env` da:

```
DATABASE_URL=postgresql+asyncpg://user:parol@localhost:5432/tourbot
```

## Testlar

```bash
pip install -r requirements-dev.txt
pytest
```

## Tuzilishi

```
bot/
  __main__.py      # ishga tushirish, dispatcher
  ai.py            # Claude: savol-javob va lead aniqlash, tur yaratish, tarjima
  config.py        # .env sozlamalari
  texts.py         # uz/ru matnlar
  keyboards.py     # tugmalar
  middlewares.py   # har bir update uchun DB sessiya va foydalanuvchi
  db/              # modellar (User, Tour, Booking, Lead, ChatMessage) va so'rovlar
  handlers/        # start, tours, booking, admin, ai_chat
```

# Tour bot

Turlarni ko'rsatish, bron qilish va mijoz savollariga AI orqali javob berish uchun Telegram bot
(Python, aiogram 3, SQLAlchemy, Claude API). Bot: @maketour_bot

## Hozir nimalar bor

- `/start` → til tanlash (o'zbekcha / ruscha / inglizcha) → asosiy menyu
- **Turlar**: yo'nalish (O'zbekiston bo'ylab, Xorijga, Umra va Haj) → turlar ro'yxati → tur kartochkasi (narx, sana, bo'sh joylar), mijoz tilida
- **AI yordamchi**: mijoz istaklarini so'rab, internetdan izlanib (reyslar, vizalar, narxlar) unga moslab yangi tur tuzib beradi.
  Admin qo'shgan turlar AI'ga ta'sir qilmaydi. Mijoz bron qilmoqchi bo'lsa yoki raqamini bersa, **lead faqat adminga** boradi,
  mijoz uni ko'rmaydi
- To'lov bot ichida yo'q: menejer mijoz bilan o'zi bog'lanadi
- **Bron qilish**: necha kishi → telefon (tugma yoki qo'lda) → tasdiqlash
- Bron adminga **Tasdiqlash / Rad etish** tugmalari bilan boradi, mijozga natija xabari yuboriladi
- **Bronlarim**: mijozning bronlari va holati
- Admin: `/admin`, `/addtour` (qadamma-qadam tur qo'shish, AI ruscha va inglizchaga o'zi tarjima qiladi),
  `/aitour <qisqa tavsif>` (AI turni 3 tilda to'liq yozib beradi, admin "Saqlash" ni bosadi), `/cancel`
- Bo'sh joylar hisoblanadi: kutilayotgan va tasdiqlangan bronlar joy egallaydi, rad etilganlari bo'shatadi

## Admin guruhi (leadlar va bronlar uchun)

1. Telegram'da yangi guruh yarating va menejerlarni qo'shing.
2. Guruhga @maketour_bot ni a'zo qilib qo'shing.
3. `ADMIN_IDS` dagi admin guruhda `/setgroup` deb yozadi.

Shundan keyin yangi leadlar (ismi, raqami, nima xohlashi) va bronlar shu guruhga keladi, guruh a'zolari bronni
tasdiqlashi yoki rad etishi mumkin. Guruh ulanmagan bo'lsa yoki bot guruhdan chiqarilsa, xabarlar adminning
shaxsiy chatiga keladi. Bot guruhdagi oddiy suhbatlarga javob bermaydi.

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

## Railway'da doimiy ishlatish

1. Railway'da yangi loyiha → **Deploy from GitHub repo** → shu repo.
2. Servisga **Volume** qo'shing, mount path: `/data`.
3. **Variables**: `BOT_TOKEN`, `ADMIN_IDS`, `ANTHROPIC_API_KEY` va
   `DATABASE_URL=sqlite+aiosqlite:////data/tour_bot.db` (ma'lumotlar qayta deploy'da o'chmasligi uchun).
4. Ishga tushirish buyrug'i `railway.json` da: `python -m bot`.

Bot Railway'da ishlayotganda uni kompyuterda ishga tushirmang: bitta token bilan ikkita bot bir vaqtda ishlay olmaydi.

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

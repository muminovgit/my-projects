# Tour bot

Turlarni ko'rsatish va bron qilish uchun Telegram bot (Python, aiogram 3, SQLAlchemy).

## Hozir nimalar bor

- `/start` → til tanlash (o'zbekcha / ruscha) → asosiy menyu
- **Turlar**: faol turlar ro'yxati, tur kartochkasi (narx, sana, bo'sh joylar)
- **Bron qilish**: necha kishi → telefon (tugma yoki qo'lda) → tasdiqlash
- Bron adminga **Tasdiqlash / Rad etish** tugmalari bilan boradi, mijozga natija xabari yuboriladi
- **Bronlarim**: mijozning bronlari va holati
- Admin: `/admin`, `/addtour` (bot ichidan tur qo'shish), `/cancel`
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
`.env` fayli git'ga tushmaydi, tokenni hech qayerga yubormang.

## Ma'lumotlar bazasi

Standart holatda `tour_bot.db` (SQLite) fayli avtomatik yaratiladi.
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
  config.py        # .env sozlamalari
  texts.py         # uz/ru matnlar
  keyboards.py     # tugmalar
  middlewares.py   # har bir update uchun DB sessiya va foydalanuvchi
  db/              # modellar (User, Tour, Booking) va so'rovlar
  handlers/        # start, tours, booking, admin
```

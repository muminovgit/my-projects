LANGS = ("uz", "ru")

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "choose_lang": "Tilni tanlang / Выберите язык",
        "welcome": "Assalomu alaykum, {name}! Tur tanlash va bron qilish uchun menyudan foydalaning.",
        "btn_tours": "🌍 Turlar",
        "btn_my_bookings": "📋 Bronlarim",
        "btn_contacts": "📞 Aloqa",
        "btn_lang": "🌐 Til",
        "btn_book": "✅ Bron qilish",
        "btn_back": "⬅️ Orqaga",
        "btn_send_phone": "📱 Raqamni yuborish",
        "btn_confirm": "✅ Tasdiqlash",
        "btn_cancel": "❌ Bekor qilish",
        "no_tours": "Hozircha faol turlar yo'q.",
        "tours_title": "Mavjud turlar:",
        "tour_card": "<b>{title}</b>\n\n{description}\n\n💵 Narxi: {price} {currency}\n📅 Sana: {date}\n🪑 Bo'sh joylar: {free}",
        "date_tbd": "kelishiladi",
        "tour_not_found": "Tur topilmadi.",
        "no_seats": "Kechirasiz, bu turda bo'sh joy qolmadi.",
        "ask_people": "Necha kishi borasiz? (1 dan {max} gacha raqam yozing)",
        "bad_people": "Iltimos, 1 dan {max} gacha raqam yozing.",
        "ask_phone": "Telefon raqamingizni yuboring (tugma orqali yoki +998XXXXXXXXX ko'rinishida).",
        "bad_phone": "Raqam noto'g'ri. Masalan: +998901234567",
        "confirm_booking": "Tekshiring:\n\n🌍 {title}\n👥 {people} kishi\n📱 {phone}\n💵 Jami: {total} {currency}\n\nTasdiqlaysizmi?",
        "booking_sent": "Rahmat! So'rovingiz #{id} qabul qilindi. Menejer tez orada bog'lanadi.",
        "booking_cancelled": "Bron bekor qilindi.",
        "booking_confirmed_user": "✅ #{id} bronningiz tasdiqlandi: {title}",
        "booking_rejected_user": "❌ #{id} bronningiz rad etildi: {title}. Savollar bo'lsa, biz bilan bog'laning.",
        "no_bookings": "Sizda hali bron yo'q.",
        "my_bookings_title": "Sizning bronlaringiz:",
        "status_pending": "⏳ kutilmoqda",
        "status_confirmed": "✅ tasdiqlangan",
        "status_rejected": "❌ rad etilgan",
        "contacts": "📞 Aloqa uchun: admin bilan bog'laning.",
        "lang_set": "Til o'zgartirildi.",
    },
    "ru": {
        "choose_lang": "Tilni tanlang / Выберите язык",
        "welcome": "Здравствуйте, {name}! Выберите тур и забронируйте его через меню.",
        "btn_tours": "🌍 Туры",
        "btn_my_bookings": "📋 Мои брони",
        "btn_contacts": "📞 Контакты",
        "btn_lang": "🌐 Язык",
        "btn_book": "✅ Забронировать",
        "btn_back": "⬅️ Назад",
        "btn_send_phone": "📱 Отправить номер",
        "btn_confirm": "✅ Подтвердить",
        "btn_cancel": "❌ Отмена",
        "no_tours": "Сейчас нет активных туров.",
        "tours_title": "Доступные туры:",
        "tour_card": "<b>{title}</b>\n\n{description}\n\n💵 Цена: {price} {currency}\n📅 Дата: {date}\n🪑 Свободных мест: {free}",
        "date_tbd": "по договорённости",
        "tour_not_found": "Тур не найден.",
        "no_seats": "К сожалению, свободных мест нет.",
        "ask_people": "Сколько человек поедет? (число от 1 до {max})",
        "bad_people": "Пожалуйста, введите число от 1 до {max}.",
        "ask_phone": "Отправьте номер телефона (кнопкой или в формате +998XXXXXXXXX).",
        "bad_phone": "Неверный номер. Например: +998901234567",
        "confirm_booking": "Проверьте:\n\n🌍 {title}\n👥 {people} чел.\n📱 {phone}\n💵 Итого: {total} {currency}\n\nПодтверждаете?",
        "booking_sent": "Спасибо! Заявка #{id} принята. Менеджер скоро свяжется с вами.",
        "booking_cancelled": "Бронирование отменено.",
        "booking_confirmed_user": "✅ Ваша бронь #{id} подтверждена: {title}",
        "booking_rejected_user": "❌ Ваша бронь #{id} отклонена: {title}. Если есть вопросы, свяжитесь с нами.",
        "no_bookings": "У вас пока нет броней.",
        "my_bookings_title": "Ваши брони:",
        "status_pending": "⏳ ожидает",
        "status_confirmed": "✅ подтверждена",
        "status_rejected": "❌ отклонена",
        "contacts": "📞 Для связи обратитесь к администратору.",
        "lang_set": "Язык изменён.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["uz"]).get(key) or TEXTS["uz"][key]
    return text.format(**kwargs) if kwargs else text


def all_variants(key: str) -> set[str]:
    """Every translation of a button label, for matching reply-keyboard presses."""
    return {TEXTS[lang][key] for lang in LANGS}

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def terms_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="✅ SHARTLARGA ROZIMAN", callback_data="terms_accept")]]
    )


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["📣 REKLAMA YUBORISH"],
            ["🔎 QIDIRISH"],
            ["📄 USERLAR RO'YHATI TEXT"],
            ["🧾 USERLAR RO'YHATI PDF"],
        ],
        resize_keyboard=True,
    )

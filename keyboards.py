from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def terms_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="SHARTLARGA ROZIMAN", callback_data="terms_accept")]]
    )


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text="Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def admin_menu(active_count=None):
    active_label = "FAOL USERLAR"
    if active_count is not None:
        active_label = f"FAOL USERLAR ({active_count})"

    return ReplyKeyboardMarkup(
        [
            ["REKLAMA YUBORISH"],
            ["QIDIRISH"],
            ["USERLAR RO'YHATI TEXT"],
            ["USERLAR RO'YHATI PDF"],
            [active_label],
        ],
        resize_keyboard=True,
    )

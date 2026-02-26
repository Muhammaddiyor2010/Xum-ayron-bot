import logging
import asyncio
import random
import re
from pathlib import Path

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_PASSWORD
from db import (
    init_db,
    upsert_user,
    update_instagram,
    update_real_name,
    update_phone,
    set_metrics,
    get_user,
    get_all_users,
    get_active_users,
    touch_user,
)
from keyboards import terms_keyboard, phone_keyboard, admin_menu
from utils_exports import export_users_xlsx, export_users_pdf


logging.basicConfig(level=logging.INFO)

TERMS_TEXT = (
    "📌 SHARTLAR:\n"
    "1) Videoda XUM Ayron chiroyli kadrlarda bo'lishi kerak.\n"
    "2) XUM AYRON akkaunti belgilanggan (atmetka qilingan) bo'lishi shart.\n"
    "3) Videoning Instagram linkini bizga tashlashingiz kerak.\n\n"
    "🧾 Davom etish uchun pastdagi tugmani bosing."
)

INSTAGRAM_RE = re.compile(
    r"^https?://(www\.)?instagram\.com/(reel|p|tv)/[A-Za-z0-9_\-]+/?(\?.*)?$",
    re.IGNORECASE,
)

admin_ids = set()

# User flow states
WAITING_INSTAGRAM, WAITING_NAME, WAITING_PHONE = range(3)

# Admin flow states
ADMIN_LOGIN, SEARCH_USER_ID, BROADCAST = range(100, 103)


def is_admin(user_id: int) -> bool:
    return user_id in admin_ids


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username, user.full_name)
    await update.message.reply_text("Salom! Xush kelibsiz.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(TERMS_TEXT, reply_markup=terms_keyboard())


async def accept_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text("🎬 Video linkini yuboring:")
    return WAITING_INSTAGRAM


async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    text = (update.message.text or "").strip()
    if not INSTAGRAM_RE.match(text):
        await update.message.reply_text("❌ Xatolik: Instagram link emas. Qayta yuboring.")
        return WAITING_INSTAGRAM
    update_instagram(update.effective_user.id, text)
    await _react_positive(update, context)
    await update.message.reply_text("🙂 Ismingizni yozing:")
    return WAITING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("⚠️ Ism bo'sh bo'lmasligi kerak. Qayta kiriting.")
        return WAITING_NAME
    update_real_name(update.effective_user.id, name)
    await update.message.reply_text("📞 Telefon raqamingizni tugma orqali yuboring.", reply_markup=phone_keyboard())
    return WAITING_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    if not update.message.contact or not update.message.contact.phone_number:
        await update.message.reply_text("⚠️ Iltimos, telefon raqamini tugma orqali yuboring.")
        return WAITING_PHONE
    update_phone(update.effective_user.id, update.message.contact.phone_number)
    await update.message.reply_text("✅ Rahmat! Ma'lumotlaringiz saqlandi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    await update.message.reply_text("🔐 Admin parolni kiriting:")
    return ADMIN_LOGIN


async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    if (update.message.text or "").strip() == ADMIN_PASSWORD:
        admin_ids.add(update.effective_user.id)
        await update.message.reply_text("✅ Admin panelga xush kelibsiz.", reply_markup=admin_menu())
        return ConversationHandler.END
    await update.message.reply_text("❌ Noto'g'ri parol.")
    return ADMIN_LOGIN


async def admin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    touch_user(update.effective_user.id)
    text = (update.message.text or "").strip()
    if text == "📣 REKLAMA YUBORISH":
        await update.message.reply_text("📣 Reklama kontentini yuboring (text/rasm/video/link).")
        return BROADCAST
    if text == "🔎 QIDIRISH":
        await update.message.reply_text("🔎 Qidirish uchun User ID kiriting:")
        return SEARCH_USER_ID
    if text == "📄 USERLAR RO'YHATI TEXT":
        await send_users_list_text(update, context)
        return ConversationHandler.END
    if text == "🧾 USERLAR RO'YHATI PDF":
        await send_users_list_pdf(update, context)
        return ConversationHandler.END
    return ConversationHandler.END


async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    touch_user(update.effective_user.id)
    try:
        user_id = int((update.message.text or "").strip())
    except ValueError:
        await update.message.reply_text("⚠️ User ID raqam bo'lishi kerak.")
        return SEARCH_USER_ID
    row = get_user(user_id)
    if not row:
        await update.message.reply_text("❌ Bunday user topilmadi.")
        return SEARCH_USER_ID
    (
        tg_id,
        username,
        tg_name,
        ig_link,
        real_name,
        phone,
        likes,
        views,
        rating,
        created_at,
    ) = row
    await update.message.reply_text(
        "Topildi:\n"
        f"ID: {tg_id}\n"
        f"Username: @{username}\n"
        f"Telegram name: {tg_name}\n"
        f"Instagram: {ig_link}\n"
        f"Ism: {real_name}\n"
        f"Telefon: {phone}\n"
        f"Likes: {likes}\n"
        f"Views: {views}\n"
        f"Reyting: {rating}\n"
        f"Created: {created_at}",
        reply_markup=admin_menu(),
    )
    return ConversationHandler.END


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    touch_user(update.effective_user.id)
    users = get_active_users(90)
    sent = 0
    failed = 0
    await update.message.reply_text("🚀 Reklama yuborish boshlandi (oxirgi 90 kun aktiv userlar). Iltimos kuting...")
    for row in users:
        user_id = row[0]
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            continue
    await update.message.reply_text(
        f"✅ Yuborildi: {sent} ta. ❌ Xato: {failed} ta.",
        reply_markup=admin_menu(),
    )
    return ConversationHandler.END


async def send_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    users = get_all_users()
    export_dir = Path(__file__).with_name("exports")
    export_dir.mkdir(exist_ok=True)
    xlsx_path = export_dir / "users.xlsx"
    pdf_path = export_dir / "users.pdf"
    export_users_xlsx(users, xlsx_path)
    export_users_pdf(users, pdf_path)
    await update.message.reply_document(document=str(xlsx_path), caption="📄 Users ro'yhati (Excel)")
    await update.message.reply_document(document=str(pdf_path), caption="📄 Users ro'yhati (PDF)")


async def send_users_list_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    users = get_all_users()
    if not users:
        await update.message.reply_text("ℹ️ Hozircha user yo'q.", reply_markup=admin_menu())
        return
    lines = []
    for row in users:
        tg_id, username, tg_name, ig_link, real_name, phone, *_ = row
        line = (
            f"🆔 {tg_id} | @{username or '-'} | {tg_name or '-'} | "
            f"📷 {ig_link or '-'} | 👤 {real_name or '-'} | 📞 {phone or '-'}"
        )
        lines.append(line)
    text = "📄 USERLAR RO'YHATI (TEXT)\n" + "\n".join(lines)
    # Telegram limit: split if too long
    for chunk in _split_text(text, 3500):
        await update.message.reply_text(chunk)
    await update.message.reply_text("✅ Tugadi.", reply_markup=admin_menu())


async def send_users_list_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    touch_user(update.effective_user.id)
    users = get_all_users()
    export_dir = Path(__file__).with_name("exports")
    export_dir.mkdir(exist_ok=True)
    pdf_path = export_dir / "users.pdf"
    export_users_pdf(users, pdf_path)
    await update.message.reply_document(document=str(pdf_path), caption="🧾 Users ro'yhati (PDF)")


def _split_text(text: str, limit: int):
    parts = []
    buf = []
    size = 0
    for line in text.split("\n"):
        add_len = len(line) + 1
        if size + add_len > limit and buf:
            parts.append("\n".join(buf))
            buf = [line]
            size = len(line) + 1
        else:
            buf.append(line)
            size += add_len
    if buf:
        parts.append("\n".join(buf))
    return parts


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def _react_positive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reactions = ["👍", "🔥", "👏", "😍", "✅", "🎉"]
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=random.choice(reactions),
        )
    except Exception:
        pass


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo'q. Env varga BOT_TOKEN qo'ying.")
    init_db()

    # Python 3.14: create and set an event loop explicitly
    asyncio.set_event_loop(asyncio.new_event_loop())

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    user_flow = ConversationHandler(
        entry_points=[CallbackQueryHandler(accept_terms, pattern="^terms_accept$")],
        states={
            WAITING_INSTAGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram)],
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            WAITING_PHONE: [MessageHandler(filters.CONTACT, handle_phone)],
        },
        fallbacks=[CommandHandler("start", cmd_start), CommandHandler("cancel", cancel)],
    )

    admin_login_flow = ConversationHandler(
        entry_points=[CommandHandler("admin", cmd_admin)],
        states={ADMIN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_login)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    admin_actions_flow = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(📣 REKLAMA YUBORISH|🔎 QIDIRISH|📄 USERLAR RO'YHATI TEXT|🧾 USERLAR RO'YHATI PDF)$"), admin_menu_router)],
        states={
            SEARCH_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_user)],
            BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, admin_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(user_flow)
    app.add_handler(admin_login_flow)
    app.add_handler(admin_actions_flow)

    app.run_polling()


if __name__ == "__main__":
    main()

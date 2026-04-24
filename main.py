import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
user_data = {}

# ===== AI =====
def detect_category(text):
    text = text.lower()
    if any(w in text for w in ["код", "бот", "сайт"]):
        return "IT"
    if any(w in text for w in ["инстаграм", "реклама", "smm"]):
        return "SMM"
    if any(w in text for w in ["дизайн", "логотип", "баннер"]):
        return "Дизайн"
    return "Другое"

# ===== DB =====
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        description TEXT,
        payment INTEGER,
        location TEXT,
        employer_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👤 Работник", "🏢 Работодатель"]]

    await update.message.reply_text(
        "🤖 Я AI-ассистент JobTab.\nКто вы?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    # ROLE
    if text == "👤 Работник":
        user_data[user_id] = {"role": "worker"}
        await update.message.reply_text("Введите имя:")
        return

    if text == "🏢 Работодатель":
        user_data[user_id] = {"role": "employer"}
        await update.message.reply_text("Опишите задачу:")
        return

    # ===== WORKER =====
    if user_data[user_id].get("role") == "worker":

        if "name" not in user_data[user_id]:
            user_data[user_id]["name"] = text

            contact_btn = KeyboardButton("📱 Отправить номер", request_contact=True)
            keyboard = [[contact_btn]]

            await update.message.reply_text(
                "Отправьте номер:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        if "phone" not in user_data[user_id]:
            if update.message.contact:
                user_data[user_id]["phone"] = update.message.contact.phone_number
                await update.message.reply_text("Введите район:")
            else:
                await update.message.reply_text("Нажмите кнопку для отправки номера")
            return

        if "location" not in user_data[user_id]:
            user_data[user_id]["location"] = text

            keyboard = [["IT", "SMM", "Дизайн", "Любое"]]
            await update.message.reply_text("Выберите навык:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return

        if text in ["IT", "SMM", "Дизайн", "Любое"]:
            await show_tasks(update, text, user_data[user_id])
            return

    # ===== EMPLOYER =====
    if user_data[user_id].get("role") == "employer":

        if "description" not in user_data[user_id]:
            user_data[user_id]["description"] = text
            category = detect_category(text)
            user_data[user_id]["category"] = category

            await update.message.reply_text(f"AI категория: {category}")
            await update.message.reply_text("Введите оплату:")
            return

        if "payment" not in user_data[user_id]:
            try:
                user_data[user_id]["payment"] = int(text.replace(" ", ""))
                await update.message.reply_text("Введите район:")
            except:
                await update.message.reply_text("Введите число")
            return

        if "location" not in user_data[user_id]:
            user_data[user_id]["location"] = text

            save_task(user_id, user_data[user_id])
            await update.message.reply_text("✅ Задача сохранена")
            user_data[user_id] = {}
            return

# ===== SAVE =====
def save_task(user_id, data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO tasks (category, description, payment, location, employer_id)
    VALUES (?, ?, ?, ?, ?)
    """, (data["category"], data["description"], data["payment"], data["location"], user_id))

    conn.commit()
    conn.close()

# ===== SHOW =====
async def show_tasks(update, skill, worker):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if skill == "Любое":
        cursor.execute("SELECT id, description, payment, location FROM tasks")
    else:
        cursor.execute("SELECT id, description, payment, location FROM tasks WHERE category=?", (skill,))

    tasks = cursor.fetchall()

    for t in tasks:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Откликнуться", callback_data=f"apply_{t[0]}")]
        ])

        await update.message.reply_text(
            f"{t[1]}\n💰 {t[2]} тг\n📍 {t[3]}",
            reply_markup=keyboard
        )

    conn.close()

# ===== APPLY =====
async def apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    task_id = int(query.data.split("_")[1])

    worker = user_data.get(user_id, {})

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT employer_id FROM tasks WHERE id=?", (task_id,))
    employer_id = cursor.fetchone()[0]

    await context.bot.send_message(
        chat_id=employer_id,
        text=f"📩 Новый отклик!\n\n👤 {worker.get('name')}\n📱 {worker.get('phone')}"
    )

    await query.message.reply_text("✅ Отклик отправлен")

    conn.close()

# ===== MAIN =====
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.CONTACT, handle))
    app.add_handler(CallbackQueryHandler(apply))

    app.run_polling()
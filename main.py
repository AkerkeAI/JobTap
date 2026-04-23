import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

print("🚀 BOT FILE LOADED")

TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN:", TOKEN)

# ===== DATABASE =====
def init_db():
    print("📦 Initializing DB...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        role TEXT,
        age INTEGER,
        location TEXT,
        skills TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        category TEXT,
        description TEXT,
        payment INTEGER,
        location TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_id INTEGER
    )
    """)

    conn.commit()
    conn.close()
    print("✅ DB READY")

user_data = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 /start received")
    keyboard = [["👤 Работник", "🏢 Работодатель"]]
    await update.message.reply_text(
        "Кто вы?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===== HANDLE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    print(f"💬 Message: {text}")

    if user_id not in user_data:
        user_data[user_id] = {}

    # ROLE
    if text == "👤 Работник":
        user_data[user_id]["role"] = "worker"
        await update.message.reply_text("Введите ваш возраст:")
        return

    if text == "🏢 Работодатель":
        user_data[user_id]["role"] = "employer"
        keyboard = [["Простая задача", "Навыковая задача"]]
        await update.message.reply_text("Выберите тип задачи:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    # AGE
    if "age" not in user_data[user_id] and user_data[user_id].get("role") == "worker":
        try:
            age = int(text)
            if age < 14:
                await update.message.reply_text("Вам пока нельзя работать.")
                return
            user_data[user_id]["age"] = age
            await update.message.reply_text("Введите ваш район:")
        except:
            await update.message.reply_text("Введите число.")
        return

    # LOCATION WORKER
    if "location" not in user_data[user_id] and user_data[user_id].get("role") == "worker":
        user_data[user_id]["location"] = text
        keyboard = [["Простые задания", "Работа по навыкам"]]
        await update.message.reply_text("Что вы ищете?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    # WORKER CHOICE
    if text == "Простые задания":
        show_tasks(update, "simple")
        return

    if text == "Работа по навыкам":
        show_tasks(update, "skill")
        return

    # EMPLOYER TYPE
    if text == "Простая задача":
        user_data[user_id]["task_type"] = "simple"
        await update.message.reply_text("Опишите задачу:")
        return

    if text == "Навыковая задача":
        user_data[user_id]["task_type"] = "skill"
        keyboard = [["SMM", "IT", "Дизайн"]]
        await update.message.reply_text("Выберите категорию:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    # CATEGORY ONLY FOR SKILL
    if user_data[user_id].get("task_type") == "skill" and "category" not in user_data[user_id]:
        user_data[user_id]["category"] = text
        await update.message.reply_text("Опишите задачу:")
        return

    # DESCRIPTION
    if "description" not in user_data[user_id] and "task_type" in user_data[user_id]:
        user_data[user_id]["description"] = text
        await update.message.reply_text("Введите оплату:")
        return

    # PAYMENT
    if "payment" not in user_data[user_id]:
        try:
            user_data[user_id]["payment"] = int(text)
            await update.message.reply_text("Введите район:")
        except:
            await update.message.reply_text("Введите число.")
        return

    # LOCATION TASK
    if "task_location" not in user_data[user_id]:
        user_data[user_id]["task_location"] = text

        save_task(user_data[user_id])

        await update.message.reply_text("✅ Задача сохранена!")
        user_data[user_id] = {}
        return


# SAVE TASK
def save_task(data):
    print("💾 Saving task...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    category = data.get("category") if data["task_type"] == "skill" else None

    cursor.execute("""
    INSERT INTO tasks (type, category, description, payment, location)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data["task_type"],
        category,
        data["description"],
        data["payment"],
        data["task_location"]
    ))

    conn.commit()
    conn.close()
    print("✅ Task saved")


# SHOW TASKS
def show_tasks(update, task_type):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT description, payment, location FROM tasks WHERE type=?", (task_type,))
    tasks = cursor.fetchall()

    if not tasks:
        update.message.reply_text("Нет задач.")
        return

    for t in tasks:
        update.message.reply_text(f"{t[0]}\n💰 {t[1]} тг\n📍 {t[2]}")

    conn.close()


# MAIN
if __name__ == "__main__":
    print("🔥 BOT STARTING...")

    init_db()

    if not TOKEN:
        print("❌ TOKEN NOT FOUND")
    else:
        print("✅ TOKEN FOUND")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()
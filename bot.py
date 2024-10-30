import json
import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

load_dotenv()

DATA_FILE = "todo_data.json"

ADDING_TASK, DELETING_TASK = 1, 2

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [["/add"], ["/delete"], ["/list"], ["/organize"], ["/help"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "مرحبًا! أنا بوت قائمة المهام. يمكنك استخدام الأوامر التالية:\n"
        "/add - لإضافة مهمة جديدة\n"
        "/list - لعرض قائمة المهام\n"
        "/delete - لحذف مهمة معينة\n"
        "/organize - لتنظيم المهام\n"
        "/help - لعرض قائمة الأوامر",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "الأوامر المتاحة:\n"
        "/add - لإضافة مهمة جديدة\n"
        "/list - لعرض قائمة المهام\n"
        "/delete - لحذف مهمة معينة\n"
        "/organize - لتنظيم المهام"
    )

async def add_task_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("يرجى كتابة المهمة التي تريد إضافتها:", reply_markup=ReplyKeyboardRemove())
    return ADDING_TASK

async def add_task(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    task = update.message.text

    data = load_data()
    if user_id not in data:
        data[user_id] = []

    data[user_id].append(task)
    save_data(data)

    await update.message.reply_text(f"تمت إضافة المهمة: {task}")

    keyboard = [["/add"], ["/delete"], ["/list"], ["/organize"], ["/help"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("يمكنك إضافة المزيد من المهام أو استخدام أوامر أخرى:", reply_markup=reply_markup)

    return ConversationHandler.END

async def list_tasks(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]:
        await update.message.reply_text("قائمة المهام فارغة.")
        return

    tasks = "\n".join([f"{idx + 1}. {task}" for idx, task in enumerate(data[user_id])])
    await update.message.reply_text(f"قائمة مهامك:\n{tasks}")

async def delete_task_start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]:
        await update.message.reply_text("قائمة المهام فارغة، لا يوجد مهام لحذفها.")
        return ConversationHandler.END

    tasks = "\n".join([f"{idx + 1}. {task}" for idx, task in enumerate(data[user_id])])
    await update.message.reply_text(f"يرجى كتابة رقم المهمة التي تريد حذفها:\n\n{tasks}", reply_markup=ReplyKeyboardRemove())
    
    return DELETING_TASK

async def delete_task(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    data = load_data()

    try:
        task_index = int(update.message.text) - 1
        if 0 <= task_index < len(data[user_id]):
            removed_task = data[user_id].pop(task_index)
            save_data(data)
            await update.message.reply_text(f"تم حذف المهمة: {removed_task}")
        else:
            await update.message.reply_text("الرقم غير صحيح. يرجى التأكد من اختيار رقم مهمة صالح.")
    except (IndexError, ValueError):
        await update.message.reply_text("يرجى كتابة رقم المهمة بشكل صحيح.")

    keyboard = [["/add"], ["/delete"], ["/list"], ["/organize"], ["/help"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("يمكنك إضافة المزيد من المهام أو استخدام أوامر أخرى:", reply_markup=reply_markup)

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def organize_tasks(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]:
        await update.message.reply_text("لا توجد مهام لتنظيمها.")
        return

    tasks = data[user_id]
    tasks_list = "\n".join(tasks)

    chatgpt_api_key = os.getenv("CHATGPT_API_KEY")  # احصل على API Key من متغير البيئة
    headers = {
        "Authorization": f"Bearer {chatgpt_api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"رتب هذه المهام حسب الأهمية والضرورة بنفس اللغة دون إضافة نصوص إضافية:\n{tasks_list}"
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        gpt_response = response.json()["choices"][0]["message"]["content"]
        await update.message.reply_text(gpt_response)
    else:
        await update.message.reply_text("حدث خطأ أثناء الاتصال بـ ChatGPT. يرجى المحاولة لاحقًا.")

def main():
    # الحصول على التوكن من متغير بيئي لأمان أفضل
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("الرجاء تعيين متغير بيئي للتوكن")
        return

    application = Application.builder().token(token).build()

    add_task_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_task_start)],
        states={ADDING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    delete_task_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_task_start)],
        states={DELETING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_task)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("organize", organize_tasks))  # إضافة الأمر لتنظيم المهام
    application.add_handler(add_task_handler)
    application.add_handler(delete_task_handler)

    application.run_polling()

if __name__ == "__main__":
    main()

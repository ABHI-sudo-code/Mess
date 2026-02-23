import os
import pandas as pd
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ----------------
# Get token from environment variable
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")

# Valid meals
VALID_MEALS = ["breakfast", "lunch", "snacks", "dinner"]

# Base directory for menu.xlsx
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(BASE_DIR, "menu.xlsx")


# ---------------- MENU LOADING ----------------
def build_menu():
    try:
        df = pd.read_excel(MENU_FILE)
        df.columns = df.columns.str.strip()
        required_columns = ["Day", "Breakfast", "Lunch", "Snacks", "Dinner"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        menu = {}
        for _, row in df.iterrows():
            day = str(row["Day"]).strip().lower()
            menu[day] = {
                "breakfast": str(row["Breakfast"]).strip(),
                "lunch": str(row["Lunch"]).strip(),
                "snacks": str(row["Snacks"]).strip(),
                "dinner": str(row["Dinner"]).strip(),
            }
        return menu

    except Exception as e:
        print("ERROR loading Excel:", e)
        return {}


menu_data = build_menu()
VALID_DAYS = list(menu_data.keys())


# ---------------- SAFE REPLY ----------------
async def safe_reply(update, message):
    try:
        await update.message.reply_text(message, parse_mode="Markdown")
    except:
        await update.message.reply_text(message)


# ---------------- COMMAND HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply(update,
        "Welcome to Mess Menu Bot\n\n"
        "Commands:\n"
        "/today → Full menu for today\n"
        "/day monday → Full menu for a day\n"
        "/help → How to use\n\n"
        "Or type: monday breakfast"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply(update,
        "Usage Guide:\n\n"
        "• Get today's menu → /today\n"
        "• Get full menu → /day monday\n"
        "• Get specific meal → monday lunch\n\n"
        "Valid meals: breakfast, lunch, snacks, dinner"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not menu_data:
        await safe_reply(update, "Menu data not available.")
        return
    today_day = datetime.datetime.today().strftime("%A").lower()
    if today_day not in menu_data:
        await safe_reply(update, "No menu found for today.")
        return
    await send_full_day(update, today_day)


async def day_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_reply(update, "Usage: /day monday")
        return
    day = context.args[0].lower()
    if day not in VALID_DAYS:
        await safe_reply(update, f"Invalid day.\nAvailable days:\n{', '.join(VALID_DAYS)}")
        return
    await send_full_day(update, day)


async def send_full_day(update: Update, day: str):
    data = menu_data.get(day)
    if not data:
        await safe_reply(update, "Menu not available.")
        return
    response = (
        f"*{day.capitalize()} Menu*\n\n"
        f"*Breakfast*\n{data['breakfast']}\n\n"
        f"*Lunch*\n{data['lunch']}\n\n"
        f"*Snacks*\n{data['snacks']}\n\n"
        f"*Dinner*\n{data['dinner']}"
    )
    await safe_reply(update, response)


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not menu_data:
        await safe_reply(update, "Menu data is not loaded properly.")
        return

    text = update.message.text.strip().lower()
    if not text:
        await safe_reply(update, "Please type something like: monday breakfast")
        return

    words = text.split()
    if len(words) == 1:
        if words[0] in VALID_DAYS:
            await send_full_day(update, words[0])
        elif words[0] in VALID_MEALS:
            await safe_reply(update, "Please specify the day.\nExample: monday breakfast")
        else:
            await safe_reply(update, "Unrecognized input.\nType /help for guidance.")
        return

    if len(words) >= 2:
        day, meal = words[0], words[1]
        if day not in VALID_DAYS:
            await safe_reply(update, f"Invalid day.\nAvailable days:\n{', '.join(VALID_DAYS)}")
            return
        if meal not in VALID_MEALS:
            await safe_reply(update, f"Invalid meal.\nValid meals:\n{', '.join(VALID_MEALS)}")
            return
        response = menu_data[day].get(meal)
        if not response or response.lower() == "nan":
            await safe_reply(update, "No data available for this selection.")
            return
        formatted = f"*{day.capitalize()} - {meal.capitalize()}*\n\n{response}"
        await safe_reply(update, formatted)
        return

    await safe_reply(update, "Invalid format. Type /help for usage.")


# ---------------- RUN BOT ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("today", today))
app.add_handler(CommandHandler("day", day_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running with polling...")

# Use polling (simplest for Render)
app.run_polling()

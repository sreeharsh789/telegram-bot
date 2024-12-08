import os
import asyncio
from typing import Final, Dict
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
from datetime import datetime, timedelta

TOKEN: Final = os.getenv('TELEGRAM_TOKEN') or '7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I'
BOT_USERNAME: Final = '@eFootball_Tournamentsbot'

# Dictionary to store registered users (adjusted to store usernames)
tournament_slots = {
    1: None,
    2: None,
}

# Set to store registered users for each tournament (dictionary with tournament ID as key)
registered_user_ids = {}

# Dictionary to store last registration time for each user (user ID as key)
user_last_register_time: Dict[int, datetime] = {}

async def reset_tournament_slots_after_delay():
    global tournament_slots
    # Wait for 10 minutes (600 seconds)
    await asyncio.sleep(10 * 60)
    # Reset tournament slots
    tournament_slots = {1: None, 2: None}
    # Notify the group that slots have been reset
    print("Tournament slots have been reset.")

# Function to handle the /register command
async def register_command(update: Update, context: CallbackContext) -> None:
    global tournament_slots, registered_user_ids, user_last_register_time

    # Get the user and their ID
    user = update.effective_user
    user_id = user.id
    if not user.username:
        await update.message.reply_text("Please set your username first to register for the tournament.")
        return

    # Check cooldown period (10 minutes)
    now = datetime.utcnow()
    last_register_time = user_last_register_time.get(user_id)
    if last_register_time and now - last_register_time < timedelta(minutes=10):
        cooldown_remaining = (last_register_time + timedelta(minutes=10)) - now
        await update.message.reply_text(f"You can register again in {cooldown_remaining.seconds // 60} minutes and {cooldown_remaining.seconds % 60} seconds.")
        return

    # Update user's last registration time
    user_last_register_time[user_id] = now

    # Check if all slots are full
    if all(tournament_slots.values()):
        # Reset all slots to empty and clear registered users for the current tournament
        tournament_slots = {1: None, 2: None}
        registered_user_ids.pop(get_current_tournament_id(), None)  # Clear if current ID exists

    # Find an empty slot
    empty_slot = next((slot for slot, value in tournament_slots.items() if value is None), None)
    if empty_slot is not None:
        tournament_slots[empty_slot] = user.username
        # Add user ID to registered set for the current tournament
        current_tournament_id = get_current_tournament_id()
        registered_user_ids.setdefault(current_tournament_id, set()).add(user_id)
        await update.message.reply_text(f"Registered in Slot {empty_slot}")

        # Update the group chat with the new slots
        await update_group(update)

        # Schedule a task to reset the slots after 10 minutes
        asyncio.create_task(reset_tournament_slots_after_delay())

    else:
        await update.message.reply_text("All slots are currently full.")

# Function to get the current tournament ID (replace with your logic)
def get_current_tournament_id() -> int:
    # Replace this with logic to identify the current tournament ID from the update object or other source
    return 1  # Placeholder value, replace with actual ID retrieval

# Function to update the group chat with the current slots
async def update_group(update: Update) -> None:
    global tournament_slots

    # Check if there are any registered users
    if any(tournament_slots.values()):
        # Construct the message with current slots
        message = "<b>🛑 Tournament Slots 🛑</b>\n\n"
        for slot, value in tournament_slots.items():
            # Format each slot with the player's handle or an empty placeholder
            if value:
                player_handle = f"@{value}"
            else:
                player_handle = "_______"
            # Add the slot information to the message
            message += f"⚽️ <b>Slot {slot}:</b> {player_handle}\n"

        # Add reminders to the message
        message += "\n📍 <b>Remember to message each other to arrange the match</b>\n"
        message += "🏆 <b>All the best for the play</b>"

        # Send the message to the group chat with Markdown formatting
        await update.message.reply_text(message, parse_mode='HTML')

def handle_response(text: str) -> str:
    # Placeholder for any additional response handling logic
    return "I am here to assist you with the tournament!"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)

    print('Bot:', response)
    await update.message.reply_text(response)

# Define the keyboard layout (using a nested list structure)
keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("/register")]],
    one_time_keyboard=True,  # Keyboard disappears after use
    resize_keyboard=True   # Keyboard resizes to fit chat window
)

async def handle_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_member = update.effective_message.new_chat_members

    # Send a welcome message with the registration button
    for member in new_member:
        await update.message.reply_text(
            f"Hi {member.username}, welcome to the group! Please click the button below to register for the tournament:",
            reply_markup=keyboard,
        )

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

def main():
    PORT: Final = int(os.getenv('PORT', '8443'))  # Use environment variable or default to 8443

    print('Starting bot....')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('register', register_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Add the welcome message handler
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_welcome))

    # Errors
    app.add_error_handler(error)

    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=f"https://telegram-bot-34hg.onrender.com/7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I/{TOKEN}")

    print(f"Bot is now running on port {PORT}")

if __name__ == "__main__":
    main()

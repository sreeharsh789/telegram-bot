import os
import asyncio
from typing import Final, Dict
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram import ReplyKeyboardMarkup, KeyboardButton
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

invited_count: Dict[int, int] = {}  # Tracks how many users each user has invited
# Dictionary to store last registration time for each user (user ID as key)
user_last_register_time: Dict[int, datetime] = {}

# Dictionary to store the warning count for each user
user_warning_count: Dict[int, int] = {}

async def reset_tournament_slots_after_delay():
    global tournament_slots
    # Wait for 10 minutes (600 seconds)
    await asyncio.sleep(1 * 60)
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
    if last_register_time and now - last_register_time < timedelta(minutes=1):
        cooldown_remaining = (last_register_time + timedelta(minutes=1)) - now
        await update.message.reply_text(f"You can register again in {cooldown_remaining.seconds // 60} minutes and {cooldown_remaining.seconds % 60} seconds.")
        return

    # Get the number of users the user has invited
    invited_users = invited_count.get(user_id, 0)

    # Check if the user has invited at least 2 members to the group
    if invited_users < 2:
        # Calculate how many more users the user needs to invite
        users_needed = 2 - invited_users

        # Provide feedback to the user
        await update.message.reply_text(f"You need to add {users_needed} more {'user' if users_needed == 1 else 'users'} to the group before you can register.")
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
    global flag

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
    inviter = update.effective_user  # The user who invited the new members

    # Increase inviter's count for each new member
    if inviter and inviter.id != 0:  # Skip updates where inviter is unknown (e.g., if the member joined themselves)
        invited_count[inviter.id] = invited_count.get(inviter.id, 0) + len(new_member)

    # Send a welcome message with the registration button
    await update.message.reply_text(
        f"Hi {new_member.username}, welcome to the group! Please click the button below to register for the tournament:",
        reply_markup=keyboard,
    )

    # Reset warning count for new members
    user_warning_count[new_member.id] = 0  # Set warning count to 0 for the new member's ID
    # Register the user if they click the button (handle_message logic)
    # ... (modify your existing handle_message to handle button clicks)

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

    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url="https://telegram-bot-34hg.onrender.com/7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I")

    print(f"Bot is now running on port {PORT}")

if __name__ == "__main__":
    main()

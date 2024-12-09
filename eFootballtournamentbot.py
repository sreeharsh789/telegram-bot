import os
import asyncio
from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from typing import Final, Dict
from telegram.constants import ParseMode

TOKEN: Final = os.getenv('TELEGRAM_TOKEN') or '7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I'
BOT_USERNAME: Final = '@eFootball_Tournamentsbot'

# Admin Telegram ID (replace with your ID)
ADMIN_ID = 1181844922  # Replace with your Telegram user ID


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
        # Create a button that links to the pinned message tutorial
        keyboard = InlineKeyboardMarkup([ 
            [InlineKeyboardButton("How to Set Username", url="https://t.me/efootball_paid_tournament/3059")],
            [InlineKeyboardButton("Username Setting Tutorial", url="https://t.me/efootball_paid_tournament/2868")]
        ])
        await update.message.reply_text(
            "Please set your username first to register for the tournament.",
            reply_markup=keyboard
        )
        return

    # Check cooldown period (5 minutes)
    now = datetime.utcnow()
    last_register_time = user_last_register_time.get(user_id)
    if last_register_time and now - last_register_time < timedelta(minutes=10):
        cooldown_remaining = (last_register_time + timedelta(minutes=10)) - now
        await update.message.reply_text(f"You can register again in {cooldown_remaining.seconds // 60} minutes and {cooldown_remaining.seconds % 60} seconds.")
        return

    # Record the registration attempt time
    user_last_register_time[user_id] = now

    # Send the QR code to the user
    await send_qr_code(update, context)

    # Send the QR code to the user
    await send_qr_code(update, context)

# Function to send the QR code privately to the user
async def send_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_code_path = os.path.join(os.getcwd(), 'assets', 'gpay_qr.png')  # Correct relative path

    if not os.path.exists(qr_code_path):
        await update.message.reply_text("QR code image is missing. Please contact the admin.")
        return

    try:
        with open(qr_code_path, "rb") as photo_file:
            await context.bot.send_photo(
                chat_id=update.effective_user.id,
                photo=photo_file,
                caption="Scan this QR code using GPay to pay and register."
            )
        # Notify the admin for approval
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=( 
                f"🛑 New Registration Request 🛑\n\n"
                f"👤 <b>Username:</b> @{update.effective_user.username}\n"
                f"🆔 <b>User ID:</b> {update.effective_user.id}\n\n"
                f"Use the buttons below to approve or decline."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{update.effective_user.id}")],
                [InlineKeyboardButton("❌ Decline", callback_data=f"decline_{update.effective_user.id}")]
            ])
        )
    except Exception as e:
        print(f"Error sending QR code: {e}")
        await update.message.reply_text(f"There was an issue sending the QR code. Error: {str(e)}")



# Function to handle the callback query (approve/decline)
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        # Split callback data to get action (approve/decline) and user ID
        action, user_id_str = query.data.split("_", 1)
        user_id = int(user_id_str)  # Convert user ID to integer

        if action == "approve":
            # Find an empty slot
            empty_slot = next((slot for slot, value in tournament_slots.items() if value is None), None)
            if empty_slot is not None:
                # Get the username of the registered user
                user = await context.bot.get_chat(user_id)  # Fetch the user's details
                username = user.username  # Get the username of the registered user
                if username:  # Ensure the user has a username
                    tournament_slots[empty_slot] = username  # Store registered user's username in the slot
                    await query.answer(text=f"User @{username} approved and registered in Slot {empty_slot}.")
                    await query.message.reply_text(f"✅ User @{username} approved and registered in Slot {empty_slot}.")

                    # Notify the user of successful registration
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ You have been registered successfully in Slot {empty_slot}!"
                    )

                    # Notify the group with updated slots (you need the group chat ID)
                    group_chat_id = '-1002143662557'  # Replace with your actual group chat ID
                    await update_group(group_chat_id, context)
                else:
                    await query.answer(text="The registered user does not have a username.")
                    await query.message.reply_text("User does not have a valid username, cannot register.")
            else:
                await query.answer(text="All slots are currently full.")
                await query.message.reply_text("All slots are currently full.")

        elif action == "decline":
            await query.answer(text="Registration declined.")
            await query.message.reply_text(f"❌ Registration for User ID {user_id} has been declined.")

    except Exception as e:
        print(f"Error processing callback: {e}")
        await query.answer(text="An error occurred while processing your request.")
        await query.message.reply_text(f"❌ Error: {str(e)}")

# Function to update the group chat with the current slots
async def update_group(group_chat_id: int, context: CallbackContext) -> None:
    global tournament_slots

    if any(tournament_slots.values()):
        message = "<b>🛑 Tournament Slots 🛑</b>\n\n"
        for slot, value in tournament_slots.items():
            player_handle = f"@{value}" if value else "_______"  # Display the username stored in the slot
            message += f"⚽️ <b>Slot {slot}:</b> {player_handle}\n"

        message += "\n📍 <b>Remember to message each other to arrange the match</b>\n"
        message += "🏆 <b>All the best for the play</b>"

        # Send the updated slots message to the group chat
        await context.bot.send_message(group_chat_id, message, parse_mode='HTML')


def handle_response(text: str) -> str:
    global flag

# Function to handle general messages
async def handle_message(update: Update, context: CallbackContext):
    message_type = update.message.chat.type
    text = update.message.text

    if message_type == 'group' and BOT_USERNAME in text:
        new_text = text.replace(BOT_USERNAME, '').strip()
        response = f"Handling message: {new_text}"
    else:
        response = f"Handling direct message: {text}"

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

# Error handling function
async def error(update: Update, context: CallbackContext):
    print(f'Update {update} caused error {context.error}')

def main():
    print('Starting bot....')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('register', register_command))

    # Callback Query Handler
    app.add_handler(CallbackQueryHandler(button_callback))


    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Add the welcome message handler
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_welcome))

    # Errors
    app.add_error_handler(error)

    # Start webhook (retained the webhook feature)
    PORT: Final = int(os.getenv('PORT', '8443'))  # Use environment variable or default to 8443
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url="https://telegram-bot-34hg.onrender.com/7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I")

    print(f"Bot is now running on port {PORT}")

if __name__ == "__main__":
    main()

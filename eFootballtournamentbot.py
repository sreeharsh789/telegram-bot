import os
import asyncio
from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from typing import Final, Dict
from telegram.constants import ParseMode
import telegram

TOKEN: Final = os.getenv('TELEGRAM_TOKEN') or '7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I'
BOT_USERNAME: Final = '@eFootball_Tournamentsbot'
BOT_USERNAME = '@eFootball_Tournamentsbot'  # Your bot's username

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

# A dictionary to keep track of the users who have registered for the first time
first_time_users = set()  # Initialize first_time_users set here globally

# Global set to track users who have interacted with the bot
interacted_users = set()

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
    global tournament_slots, registered_user_ids, user_last_register_time, first_time_users

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

    # Check if it's the first time the user is registering
    if user_id not in first_time_users:
        first_time_users.add(user_id)

        # Send the "Start Registration" button
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Start Registration", callback_data="start_registration")]
            ]
        )

        await update.message.reply_text(
            "Welcome! It seems like you're registering for the first time. Please click below to start the registration process.",
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

    # Send the reminder message that the user is waiting for approval
    await update.message.reply_text(
        "⏳ Please wait for admin approval.\n\n"
        "📸 Please send your payment proof after payment."
    )

# Function to send the QR code privately to the user
async def send_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_code_url = "https://i.imgur.com/CN2elEx.png"  # Replace with your actual image URL

    try:
        await context.bot.send_photo(
            chat_id=update.effective_user.id,
            photo=qr_code_url,  # Use the URL here
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
        if isinstance(e, telegram.error.Forbidden):
            # Handle the case where the bot can't send a message
            await update.message.reply_text("I am unable to send you the QR code. Please start a conversation with the bot first.")
        else:
            print(f"Error sending QR code: {e}")
            await update.message.reply_text(f"There was an issue sending the QR code. Error: {str(e)}")



# Function to handle the callback query (approve/decline)
async def button_callback(update: Update, context: CallbackContext):
    global tournament_slots

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

                    # Check if both slots are filled
                    if all(tournament_slots.values()):
                        # Notify the group with updated slots before resetting the tournament
                        group_chat_id = '-1002143662557'  # Replace with your actual group chat ID
                        await update_group(group_chat_id, context)

                        # Reset tournament slots for the next tournament
                        tournament_slots = {1: None, 2: None}

                    else:
                        # Notify the group with the updated slots
                        group_chat_id = '-1002143662557'  # Replace with your actual group chat ID
                        await update_group(group_chat_id, context)
                else:
                    await query.answer(text="The registered user does not have a username.")
                    await query.message.reply_text("User does not have a valid username, cannot register.")

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

        # Debugging: print the message content
        print("Sending to group:", message)

        try:
            # Send the updated slots message to the group chat
            await context.bot.send_message(group_chat_id, message, parse_mode='HTML')
            print("Message successfully sent to the group.")

        except Exception as e:
            # Capture and log any error when sending the message
            print(f"Error sending message to group: {e}")
            # Optionally, notify the admin about the error
            await context.bot.send_message(ADMIN_ID, f"Error sending message to group: {e}")

async def start_command(update: Update, context: CallbackContext) -> None:
    global interacted_users

    # Determine if the command is issued in a private chat or a group
    chat_type = update.message.chat.type
    user_id = update.effective_user.id

    if chat_type == "private":
        # Check if the user has interacted before
        if user_id in interacted_users:
            await update.message.reply_text("Welcome back! Use the button below to go to the group and type /register.")
        else:
            # First-time user, track them and send the registration button
            interacted_users.add(user_id)
            await update.message.reply_text("Welcome to the eFootball Tournament bot! Use the button below to join the group and type /register.")

        # Button to navigate the user to the group
        group_chat_username = "efootball_paid_tournament"  # Replace with your group's username
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Register in Group", url=f"https://t.me/{group_chat_username}")]
        ])

        await update.message.reply_text(
            "Welcome to the eFootball Tournament bot! If you need to register, please use /register in the group.",
            reply_markup=keyboard
        )

    elif chat_type in ["group", "supergroup"]:
        # Send only the registration redirection button in group chats
        bot_username = "eFootball_Tournamentsbot"  # Use dynamic bot username
        start_url = f"https://t.me/{bot_username}?start=registration"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Start Registration", url=start_url)]])
        await update.message.reply_text("Please click below to start the registration process.", reply_markup=keyboard)





# Handle callback when user clicks 'Start Registration' button
async def start_registration_callback(update: Update, context: CallbackContext) -> None:
    await update.callback_query.answer()  # Acknowledge the button click
    bot_username = "eFootball_Tournamentsbot"  # Replace with your bot's username
    start_url = f"https://t.me/{bot_username}?start=registration"

    # Send only one message with the button
    keyboard = [[InlineKeyboardButton("Start Registration", url=start_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit the original group message to add the button (avoid sending new messages)
    await update.callback_query.edit_message_text(
        "Please click below to start the registration process.",
        reply_markup=reply_markup
    )




def handle_response(text: str) -> str:
    global flag

# Function to handle general messages
async def handle_message(update: Update, context: CallbackContext):
    message = update.message
    message_type = message.chat.type
    text = message.text.lower() if message.text else ""  # Ensure text is not None

    # Check if the message is from a group or supergroup
    if message_type in ['group', 'supergroup']:
        # Check if the bot's username is mentioned or if the message is a reply to the bot's message
        if BOT_USERNAME.lower() in text or (message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id):
            # Reply with registration instructions when the bot is mentioned or when replying to its own message
            await message.reply_text("To register for the tournament, please use the /register command.")
        else:
            # Ignore other messages
            pass




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

# Main function to start the bot
def main():
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('register', register_command))
    app.add_handler(CommandHandler('start', start_command))
    # Callback Query Handler
    app.add_handler(CallbackQueryHandler(start_registration_callback, pattern="start_registration"))
    app.add_handler(CallbackQueryHandler(button_callback))


    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    # Start webhook (retained the webhook feature)
    PORT: Final = int(os.getenv('PORT', '8443'))  # Use environment variable or default to 8443
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url="https://telegram-bot-34hg.onrender.com/7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I")

    print(f"Bot is now running on port {PORT}")

if __name__ == "__main__":
    main()


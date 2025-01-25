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


# Tournament data for ₹15, ₹30, ₹50
TOURNAMENTS = {
    15: {
        "slots": {1: None, 2: None},
        "qr_code_url": "https://i.imgur.com/ZsoUhbv.png",
        "prize": 25,
    },
    30: {
        "slots": {1: None, 2: None},
        "qr_code_url": "https://i.imgur.com/aJyxHSP.png",
        "prize": 50,
    },
    50: {
        "slots": {1: None, 2: None},
        "qr_code_url": "https://i.imgur.com/nlET5gr.png",
        "prize": 80,
    },
}

user_last_register_time: Dict[int, datetime] = {}  # Cooldown timer for registration
interacted_users = set()  # Tracks users who interacted with the bot
first_time_users = set()  # Tracks first-time users

async def reset_tournament_slots_after_delay():
    global tournament_slots
    # Wait for 10 minutes (600 seconds)
    await asyncio.sleep(10 * 60)
    # Reset tournament slots
    tournament_slots = {1: None, 2: None}
    # Notify the group that slots have been reset
    print("Tournament slots have been reset.")


async def register_command(update: Update, context: CallbackContext) -> None:
    global user_last_register_time, first_time_users, interacted_users

    # Get the user and their ID
    user = update.effective_user
    user_id = user.id

    # Get the current time (UTC)
    now = datetime.utcnow()

    # Add the user to the interacted_users set immediately
    interacted_users.add(user_id)

    # Check if it's the first time the user is registering
    if user_id not in first_time_users:
        first_time_users.add(user_id)

        # Send the "Start Registration" button for first-time users
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Start Registration", callback_data="start_registration")]
            ]
        )

        await update.message.reply_text(
            "Welcome! It seems like you're registering for the first time. Please click below to start the registration process.",
            reply_markup=keyboard
        )
        return  # Exit the function for first-time users

    # Check cooldown period (10 minutes)
    last_register_time = user_last_register_time.get(user_id)
    if last_register_time and now - last_register_time < timedelta(minutes=10):
        cooldown_remaining = (last_register_time + timedelta(minutes=10)) - now
        await update.message.reply_text(f"You can register again in {cooldown_remaining.seconds // 60} minutes and {cooldown_remaining.seconds % 60} seconds.")
        return  # Skip the rest of the function if user is in cooldown

    # Record the registration attempt time
    user_last_register_time[user_id] = now

    # Inline keyboard for tournament options
# When creating the registration buttons for ₹15, ₹30, ₹50
    keyboard = [
        [InlineKeyboardButton("₹15 Tournament", callback_data=f"register_15_{user_id}")],
        [InlineKeyboardButton("₹30 Tournament", callback_data=f"register_30_{user_id}")],
        [InlineKeyboardButton("₹50 Tournament", callback_data=f"register_50_{user_id}")],
    ]

    await update.message.reply_text(
        "Choose your tournament type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    user_last_register_time[user_id] = now

    # Inline keyboard for tournament options
    keyboard = [
        [InlineKeyboardButton("₹15 Tournament", callback_data=f"register_15_{user_id}")],
        [InlineKeyboardButton("₹30 Tournament", callback_data=f"register_30_{user_id}")],
        [InlineKeyboardButton("₹50 Tournament", callback_data=f"register_50_{user_id}")],
    ]
    await update.message.reply_text(
        "Choose your tournament type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # Proceed if user has already interacted before, skipping first-time message
    # Check cooldown period (5 minutes)
    now = datetime.utcnow()
    last_register_time = user_last_register_time.get(user_id)
    if last_register_time and now - last_register_time < timedelta(minutes=10):
        cooldown_remaining = (last_register_time + timedelta(minutes=10)) - now
        await update.message.reply_text(f"You can register again in {cooldown_remaining.seconds // 60} minutes and {cooldown_remaining.seconds % 60} seconds.")
        return

    # Record the registration attempt time
    user_last_register_time[user_id] = now
    

    # Add the user to the interacted_users set after the registration process
    interacted_users.add(user_id)  # Mark this user as having interacted before



# Callback for tournament registration
async def register_tournament_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    user_id = query.from_user.id
    data = query.data

    # Ensure the callback data is structured as 'register_<tournament_type>_<user_id>'
    try:
        # Split the data to extract the tournament type and user ID
        action, tournament_type, user = data.split('_')
        tournament_type = int(tournament_type)  # Convert tournament type to integer

        if int(user) != user_id:
            # If the user ID doesn't match, show the alert message
            await context.bot.answer_callback_query(
                callback_query_id=query.id,  # Pass the query ID
                text="That's not for you! Request your own.",  # Alert text
                show_alert=True  # This ensures a popup alert is shown
            )
            return
    except ValueError:
        # Handle any errors in case the split data format is incorrect
        print(f"Error in parsing callback data: {data}")
        return

    # Proceed with tournament registration after successful check
    tournament = TOURNAMENTS[tournament_type]

    # Check which slot (1 or 2) is empty and register the user
    if tournament["slots"][1] is None:
        tournament["slots"][1] = user_id  # Assign user to Slot 1
        slot = 1
    elif tournament["slots"][2] is None:
        tournament["slots"][2] = user_id  # Assign user to Slot 2
        slot = 2
    else:
        # Both slots are filled, reset the slots and assign to Slot 1 again
        tournament["slots"] = {1: None, 2: None}
        tournament["slots"][1] = user_id  # Reassign the first user to Slot 1
        slot = 1

    # Notify user and send the QR code
    await context.bot.send_photo(
        chat_id=user_id,
        photo=tournament["qr_code_url"],
        caption=f"Scan this QR code to pay ₹{tournament_type} and register. The winner receives ₹{tournament['prize']}.",
    )

    # Notify admin for approval
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(f"🛑 New Registration Request 🛑\n\n"
              f"👤 <b>User:</b> {query.from_user.mention_html()}\n"
              f"💰 <b>Tournament:</b> ₹{tournament_type}\n"
              f"⚽ <b>Slot:</b> Slot {slot}\n\n"
              f"Approve or Decline below."),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([ 
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{tournament_type}_{user_id}_{slot}")],
            [InlineKeyboardButton("❌ Decline", callback_data=f"decline_{user_id}")],
        ]),
    )

    await query.edit_message_text(f"⏳Your registration request for ₹{tournament_type} has been sent for admin approval.\n\n"
                                   "📸 Please send your payment proof after payment.")





    
# Approve/Decline buttons handler
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[2])

    if action == "approve":
        tournament_type = int(data[1])
        slot = int(data[3])
        TOURNAMENTS[tournament_type]["slots"][slot] = user_id

        # Notify user and group
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ You are registered in ₹{tournament_type} Tournament, Slot {slot}!"
        )
        await update_group(context, tournament_type)

    elif action == "decline":
        await context.bot.send_message(chat_id=user_id, text="❌ Your registration request was declined.")
        await query.message.reply_text("Registration declined.")



# Group update function
async def update_group(context: CallbackContext, tournament_type: int):
    group_chat_id = "-1002143662557"  # Replace with your group chat ID
    tournament = TOURNAMENTS[tournament_type]

    message = f"<b>🛑 ₹{tournament_type} Tournament Slots 🛑</b>\n\n"
    for slot, user_id in tournament["slots"].items():
        player = f'<a href="tg://user?id={user_id}">Player {user_id}</a>' if user_id else "_______"
        message += f"⚽ Slot {slot}: {player}\n"

    message += f"\n🏆 Winner receives ₹{tournament['prize']}. All the best!"
    await context.bot.send_message(group_chat_id, message, parse_mode=ParseMode.HTML)

        # Debugging: print the message content
    print("Sending to group:", message)

    try:
            # Send the updated slots message to the group chat
            await context.bot.send_message(group_chat_id, message, parse_mode='HTML')
            print("Message successfully sent to the group.")
    except Exception as e:
            print(f"Error sending message to group: {e}")
            await context.bot.send_message(
                ADMIN_ID, f"Error sending message to group: {e}"
            )
    else:
            print("No players registered in tournament slots yet.")




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
        group_chat_username = "efootballtournamentX"  # Replace with your group's username
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

    # Callbacks
    app.add_handler(CallbackQueryHandler(register_tournament_callback, pattern="register_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="(approve|decline)_"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    # Start webhook (retained the webhook feature)
    PORT: Final = int(os.getenv('PORT', '8443'))  # Use environment variable or default to 8443
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url="https://telegram-bot-34hg.onrender.com/7142977655:AAF_LqsngKsGeY7c3_szb2pPY1_DhDVXo6I")

    print(f"Bot is now running on port {PORT}")
    
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()

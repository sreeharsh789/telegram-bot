import os
import asyncio
from typing import Final, Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CallbackContext
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import requests
import json
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN: Final = os.getenv('TELEGRAM_TOKEN')
BOT_USERNAME: Final = os.getenv('BOT_USERNAME', '@eFootball_Tournamentsbot')
ADMIN_ID: Final = int(os.getenv('ADMIN_ID', '1181844922'))
GROUP_CHAT_ID: Final = os.getenv('GROUP_CHAT_ID', '-1002143662557')
PAYMENT_GATEWAY_KEY: Final = os.getenv('PAYMENT_GATEWAY_KEY')
PAYMENT_GATEWAY_SECRET: Final = os.getenv('PAYMENT_GATEWAY_SECRET')
WEBHOOK_URL: Final = os.getenv('WEBHOOK_URL')

# Tournament configuration
TOURNAMENTS = {
    15: {
        "slots": {1: None, 2: None},
        "prize": 25,
        "entry_fee": 15
    },
    30: {
        "slots": {1: None, 2: None},
        "prize": 50,
        "entry_fee": 30
    },
    50: {
        "slots": {1: None, 2: None},
        "prize": 80,
        "entry_fee": 50
    },
}

# User tracking
user_last_register_time: Dict[int, datetime] = {}
interacted_users = set()
first_time_users = set()
waiting_approvals: Dict[int, List[int]] = {15: [], 30: [], 50: []}

class PaymentGateway:
    """Payment gateway integration (Razorpay example)"""
    
    @staticmethod
    def create_payment_link(amount: int, user_id: int, tournament_type: int) -> Dict:
        """Create a payment link using Razorpay API"""
        try:
            url = "https://api.razorpay.com/v1/payment_links"
            
            payload = {
                "amount": amount * 100,  # Amount in paise
                "currency": "INR",
                "accept_partial": False,
                "description": f"eFootball Tournament ₹{tournament_type} - User {user_id}",
                "customer": {
                    "name": f"User {user_id}",
                    "contact": "+919999999999",  # Default contact
                    "email": f"user{user_id}@example.com"
                },
                "notes": {
                    "user_id": str(user_id),
                    "tournament_type": str(tournament_type),
                    "authorized_user": str(user_id)  # Additional security
                },
                "notify": {
                    "sms": False,
                    "email": False
                },
                "reminder_enable": False,
                "callback_url": f"{WEBHOOK_URL}/payment-success?user_id={user_id}&tournament={tournament_type}",
                "callback_method": "get"
            }
            
            response = requests.post(
                url,
                json=payload,
                auth=(PAYMENT_GATEWAY_KEY, PAYMENT_GATEWAY_SECRET),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Payment link creation failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating payment link: {e}")
            return None
    

async def start_command(update: Update, context: CallbackContext) -> None:
    """Handle /start command"""
    global interacted_users
    
    chat_type = update.message.chat.type
    user_id = update.effective_user.id
    
    if chat_type == "private":
        interacted_users.add(user_id)
        
        group_chat_username = "efootballtournamentX"  # Replace with your group username
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Tournament Group", url=f"https://t.me/{group_chat_username}")]
        ])
        
        welcome_text = (
            "🏆 <b>Welcome to eFootball Tournament Bot!</b>\n\n"
            "🎮 Join exciting tournaments with real prizes!\n"
            "💰 Entry fees: ₹15, ₹30, ₹50\n"
            "🏅 Win amazing cash prizes!\n\n"
            "Click below to join the tournament group and use /register to participate."
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
    elif chat_type in ["group", "supergroup"]:
        bot_username = BOT_USERNAME.replace('@', '')
        start_url = f"https://t.me/{bot_username}?start=registration"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Start Registration", url=start_url)]
        ])
        
        await update.message.reply_text(
            "🏆 Ready to join the tournament? Click below to register!",
            reply_markup=keyboard
        )

async def register_command(update: Update, context: CallbackContext) -> None:
    """Handle /register command"""
    global user_last_register_time, first_time_users, interacted_users
    
    user = update.effective_user
    user_id = user.id
    now = datetime.utcnow()
    
    # Add user to interacted users
    interacted_users.add(user_id)
    
    # Check if first-time user
    if user_id not in first_time_users:
        first_time_users.add(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Start Registration", callback_data="start_registration")]
        ])
        
        await update.message.reply_text(
            "🎉 <b>Welcome to your first tournament!</b>\n\n"
            "Click below to begin the registration process.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check cooldown (10 minutes)
    last_register_time = user_last_register_time.get(user_id)
    if last_register_time and now - last_register_time < timedelta(minutes=10):
        cooldown_remaining = (last_register_time + timedelta(minutes=10)) - now
        minutes = cooldown_remaining.seconds // 60
        seconds = cooldown_remaining.seconds % 60
        
        await update.message.reply_text(
            f"⏰ <b>Cooldown Active</b>\n\n"
            f"You can register again in {minutes} minutes and {seconds} seconds.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Update last register time
    user_last_register_time[user_id] = now
    
    # Show tournament options
    keyboard = [
        [InlineKeyboardButton("💰 ₹15 Tournament (Win ₹25)", callback_data=f"register_15_{user_id}")],
        [InlineKeyboardButton("💰 ₹30 Tournament (Win ₹50)", callback_data=f"register_30_{user_id}")],
        [InlineKeyboardButton("💰 ₹50 Tournament (Win ₹80)", callback_data=f"register_50_{user_id}")],
    ]
    
    await update.message.reply_text(
        "🏆 <b>Choose Your Tournament</b>\n\n"
        "Select the tournament you want to join:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def start_registration_callback(update: Update, context: CallbackContext) -> None:
    """Handle start registration callback"""
    await update.callback_query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💰 ₹15 Tournament (Win ₹25)", callback_data=f"register_15_{update.callback_query.from_user.id}")],
        [InlineKeyboardButton("💰 ₹30 Tournament (Win ₹50)", callback_data=f"register_30_{update.callback_query.from_user.id}")],
        [InlineKeyboardButton("💰 ₹50 Tournament (Win ₹80)", callback_data=f"register_50_{update.callback_query.from_user.id}")],
    ]
    
    await update.callback_query.edit_message_text(
        "🏆 <b>Choose Your Tournament</b>\n\n"
        "Select the tournament you want to join:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def register_tournament_callback(update: Update, context: CallbackContext):
    """Handle tournament registration callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    try:
        action, tournament_type, user = data.split('_')
        tournament_type = int(tournament_type)
        
        # Verify user ID matches
        if int(user) != user_id:
            await context.bot.answer_callback_query(
                callback_query_id=query.id,
                text="❌ That's not for you! Request your own registration.",
                show_alert=True
            )
            return
            
    except ValueError:
        logger.error(f"Error parsing callback data: {data}")
        return
    
    # Create payment link
    payment_data = PaymentGateway.create_payment_link(
        amount=tournament_type,
        user_id=user_id,
        tournament_type=tournament_type
    )
    
    if not payment_data:
        await query.edit_message_text(
            "❌ <b>Payment Error</b>\n\n"
            "Unable to create payment link. Please try again later.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send payment link to user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay Now", url=payment_data.get('short_url'))],
        [InlineKeyboardButton("⚠️ Payment Security", callback_data="payment_security")]
    ])
    
    await query.edit_message_text(
        f"💳 <b>Payment Required</b>\n\n"
        f"🏆 Tournament: ₹{tournament_type}\n"
        f"💰 Entry Fee: ₹{tournament_type}\n"
        f"🏅 Prize: ₹{TOURNAMENTS[tournament_type]['prize']}\n\n"
        f"Click below to complete your payment:\n\n"
        f"⚠️ <b>IMPORTANT:</b> This payment link is personalized for you only.\n"
        f"⏰ <i>You will be automatically registered after payment.</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def payment_security_callback(update: Update, context: CallbackContext):
    """Handle payment security info callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔒 <b>Payment Security Information</b>\n\n"
        "• Each payment link is personalized and can only be used by the requesting user\n"
        "• Payment links expire after 24 hours\n"
        "• Only you can complete payment using your link\n"
        "• After successful payment, you'll be automatically registered\n"
        "• Your slot will be assigned immediately\n\n"
        "🛡️ <i>Your payment is secure and protected.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back to Payment", callback_data="back_to_payment")]
        ])
    )

async def back_to_payment_callback(update: Update, context: CallbackContext):
    """Handle back to payment callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Please use /register command to start a new registration process.",
        parse_mode=ParseMode.HTML
    )

async def approve_decline_callback(update: Update, context: CallbackContext):
    """Handle admin approval/decline"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action = data[0]
    
    if action == "approve":
        tournament_type = int(data[1])
        user_id = int(data[2])
        
        # Assign slot
        tournament = TOURNAMENTS[tournament_type]
        slot_assigned = False
        slot = None
        
        if tournament["slots"][1] is None:
            tournament["slots"][1] = user_id
            slot = 1
            slot_assigned = True
        elif tournament["slots"][2] is None:
            tournament["slots"][2] = user_id
            slot = 2
            slot_assigned = True
        else:
            # Both slots filled, overwrite slot 1 and clear slot 2
            tournament["slots"][1] = user_id
            tournament["slots"][2] = None
            slot = 1
            slot_assigned = True
        
        if slot_assigned:
            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ <b>Registration Approved!</b>\n\n"
                     f"🏆 Tournament: ₹{tournament_type}\n"
                     f"🎯 Slot: {slot}\n"
                     f"🏅 Prize: ₹{tournament['prize']}\n\n"
                     f"Good luck in the tournament!",
                parse_mode=ParseMode.HTML
            )
            
            # Remove from waiting list
            if user_id in waiting_approvals[tournament_type]:
                waiting_approvals[tournament_type].remove(user_id)
            
            # Update group
            await update_group(context, tournament_type)
            
            # Update admin message
            await query.edit_message_text(
                f"✅ <b>Approved</b>\n\n"
                f"User assigned to ₹{tournament_type} Tournament, Slot {slot}",
                parse_mode=ParseMode.HTML
            )
    
    elif action == "decline":
        user_id = int(data[1])
        
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ <b>Registration Declined</b>\n\n"
                 "Your registration request was not approved. "
                 "Please contact support if you believe this is an error.",
            parse_mode=ParseMode.HTML
        )
        
        await query.edit_message_text("❌ Registration declined.")

async def update_group(context: CallbackContext, tournament_type: int):
    """Update group with current tournament slots"""
    tournament = TOURNAMENTS[tournament_type]
    
    message = f"🛑 <b>₹{tournament_type} Tournament Slots</b> 🛑\n\n"
    
    for slot, user_id in tournament["slots"].items():
        if user_id:
            player = f'<a href="tg://user?id={user_id}">Player {user_id}</a>'
        else:
            player = "_______"
        message += f"⚽ Slot {slot}: {player}\n"
    
    message += f"\n🏆 Winner receives ₹{tournament['prize']}. All the best!"
    
    try:
        await context.bot.send_message(
            GROUP_CHAT_ID,
            message,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Group updated for ₹{tournament_type} tournament")
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        await context.bot.send_message(
            ADMIN_ID,
            f"❌ Error updating group: {e}"
        )

async def handle_message(update: Update, context: CallbackContext):
    """Handle general messages"""
    message = update.message
    message_type = message.chat.type
    text = message.text.lower() if message.text else ""
    
    if message_type in ['group', 'supergroup']:
        if BOT_USERNAME.lower() in text or (
            message.reply_to_message and 
            message.reply_to_message.from_user.id == context.bot.id
        ):
            await message.reply_text(
                "🏆 To register for tournaments, use the /register command!"
            )

async def error_handler(update: Update, context: CallbackContext):
    """Handle errors"""
    logger.error(f'Update {update} caused error {context.error}')

def main():
    """Main function to start the bot"""
    
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN not found in environment variables")
        return
    
    logger.info('Starting eFootball Tournament Bot...')
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('register', register_command))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(start_registration_callback, pattern="start_registration"))
    app.add_handler(CallbackQueryHandler(register_tournament_callback, pattern="register_"))
    app.add_handler(CallbackQueryHandler(payment_security_callback, pattern="payment_security"))
    app.add_handler(CallbackQueryHandler(back_to_payment_callback, pattern="back_to_payment"))
    app.add_handler(CallbackQueryHandler(approve_decline_callback, pattern="(approve|decline)_"))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start webhook
    PORT = int(os.getenv('PORT', '8443'))
    
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
        logger.info(f"Bot started with webhook on port {PORT}")
    else:
        app.run_polling()
        logger.info("Bot started with polling")

if __name__ == "__main__":
    main()
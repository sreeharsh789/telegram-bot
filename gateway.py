from flask import Flask, request, jsonify
import os
import asyncio
import logging
from datetime import datetime
import requests
import hmac
import hashlib
import json
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '1181844922'))
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '-1002143662557')
PAYMENT_GATEWAY_SECRET = os.getenv('PAYMENT_GATEWAY_SECRET')

# Global variables for bot communication


# Tournament slots tracking
TOURNAMENTS = {
    15: {"slots": {1: None, 2: None}, "prize": 25},
    30: {"slots": {1: None, 2: None}, "prize": 50},
    50: {"slots": {1: None, 2: None}, "prize": 80},
}

def assign_tournament_slot(user_id: int, tournament_type: int) -> dict:
    """Assign user to tournament slot"""
    try:
        tournament = TOURNAMENTS[tournament_type]
        
        # Check if slot 1 is available
        if tournament["slots"][1] is None:
            tournament["slots"][1] = user_id
            return {"slot": 1, "success": True}
        # Check if slot 2 is available
        elif tournament["slots"][2] is None:
            tournament["slots"][2] = user_id
            return {"slot": 2, "success": True}
        else:
            # Both slots filled, overwrite slot 1 and clear slot 2
            tournament["slots"][1] = user_id
            tournament["slots"][2] = None
            return {"slot": 1, "success": True}
            
    except Exception as e:
        logger.error(f"Error assigning slot: {e}")
        return {"success": False}

def update_tournament_group(tournament_type: int, user_id: int, slot: int):
    """Update group with tournament slot information"""
    try:
        tournament = TOURNAMENTS[tournament_type]
        
        message = f"🛑 <b>₹{tournament_type} Tournament Slots</b> 🛑\n\n"
        
        for slot_num, player_id in tournament["slots"].items():
            if player_id:
                player = f'<a href="tg://user?id={player_id}">Player {player_id}</a>'
            else:
                player = "_______"
            message += f"⚽ Slot {slot_num}: {player}\n"
        
        message += f"\n🏆 Winner receives ₹{tournament['prize']}. All the best!"
        
        send_telegram_message(GROUP_CHAT_ID, message)
        logger.info(f"Group updated for ₹{tournament_type} tournament")
        
    except Exception as e:
        logger.error(f"Error updating group: {e}")

def send_telegram_message(chat_id: int, text: str):
    """Send message via Telegram Bot API"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def verify_razorpay_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook signature"""
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False

def send_telegram_message_with_keyboard(chat_id: int, text: str, keyboard: dict):
    """Send message with inline keyboard via Telegram Bot API"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending Telegram message with keyboard: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Bot is running ✅',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/payment-webhook', methods=['POST'])
def payment_webhook():
    """Handle payment gateway webhooks"""
    try:
        # Get the raw payload
        payload = request.get_data(as_text=True)
        signature = request.headers.get('X-Razorpay-Signature', '')
        
        # Verify signature (for Razorpay)
        if PAYMENT_GATEWAY_SECRET and not verify_razorpay_signature(payload, signature, PAYMENT_GATEWAY_SECRET):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Parse the webhook data
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({'error': 'No data received'}), 400
        
        event = webhook_data.get('event')
        payment_data = webhook_data.get('payload', {}).get('payment_link', {})
        
        logger.info(f"Received webhook event: {event}")
        
        if event in ['payment_link.paid', 'payment.captured']:
            if event == 'payment_link.paid':
                payment_data = webhook_data.get('payload', {}).get('payment_link', {})
                payment_link_id = payment_data.get('id')
                amount = payment_data.get('amount', 0) // 100
                status = payment_data.get('status')
                customer_details = payment_data.get('customer', {})
                description = payment_data.get('description', '')
            else:  # payment.captured
                payment_data = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
                payment_link_id = payment_data.get('id')
                amount = payment_data.get('amount', 0) // 100
                status = 'captured'
                customer_details = {}
                description = payment_data.get('description', '')
            
            # Determine tournament type based on amount
            tournament_type = None
            if amount == 15:
                tournament_type = 15
            elif amount == 30:
                tournament_type = 30
            elif amount == 50:
                tournament_type = 50
            
            if tournament_type and status in ['paid', 'captured']:
                # Extract user ID from customer details or description
                user_id = None
                if 'User ' in description:
                    try:
                        user_id = int(description.split('User ')[1].split(' ')[0])
                    except:
                        pass
                
                # Try to extract from notes if description doesn't work
                if not user_id:
                    notes = payment_data.get('notes', {})
                    if isinstance(notes, dict) and 'user_id' in notes:
                        try:
                            user_id = int(notes['user_id'])
                        except:
                            pass
                
                # Security check: verify authorized user
                authorized_user = None
                if isinstance(payment_data.get('notes', {}), dict):
                    try:
                        authorized_user = int(payment_data['notes'].get('authorized_user', '0'))
                    except:
                        pass
                
                # If we have both user_id and authorized_user, they must match
                if user_id and authorized_user and user_id != authorized_user:
                    logger.warning(f"Security violation: user_id {user_id} != authorized_user {authorized_user}")
                    return jsonify({'status': 'error', 'message': 'Unauthorized payment'}), 403
                
                logger.info(f"Processing payment: Amount=₹{amount}, Tournament=₹{tournament_type}, User={user_id}")
                
                # Store payment info for bot to process
                payment_key = f"{payment_link_id}_{int(time.time())}"
                pending_payments[payment_key] = {
                    'user_id': user_id,
                    'tournament_type': tournament_type,
                    'amount': amount,
                    'payment_id': payment_link_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Notify admin about successful payment
                admin_message = (
                    f"💳 <b>Payment Received!</b>\n\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"🏆 Tournament: ₹{tournament_type}\n"
                    f"🆔 Payment ID: {payment_link_id}\n"
                    f"👤 User ID: {user_id}\n"
                    f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"Click below to approve registration:"
                )
                
                # If we have user ID, notify them too
                if user_id:
                    # Auto-assign slot instead of waiting for approval
                    slot_assigned = assign_tournament_slot(user_id, tournament_type)
                    
                    if slot_assigned:
                        slot_number = slot_assigned['slot']
                        prize = 25 if tournament_type == 15 else 50 if tournament_type == 30 else 80
                        
                        # Notify user of successful registration
                        user_message = (
                            f"✅ <b>Registration Successful!</b>\n\n"
                            f"🏆 Tournament: ₹{tournament_type}\n"
                            f"🎯 Slot: {slot_number}\n"
                            f"🏅 Prize: ₹{prize}\n\n"
                            f"Good luck in the tournament!"
                        )
                        send_telegram_message(user_id, user_message)
                        
                        # Update group with new slot assignment
                        update_tournament_group(tournament_type, user_id, slot_number)
                        
                        # Notify admin of automatic registration
                        admin_notification = (
                            f"✅ <b>Auto Registration Complete</b>\n\n"
                            f"👤 User: {user_id}\n"
                            f"💰 Tournament: ₹{tournament_type}\n"
                            f"🎯 Assigned Slot: {slot_number}\n"
                            f"💳 Payment ID: {payment_link_id}"
                        )
                        send_telegram_message(ADMIN_ID, admin_notification)
                    else:
                        # Fallback if slot assignment fails
                        user_message = (
                            f"✅ <b>Payment Confirmed!</b>\n\n"
                            f"💰 Tournament: ₹{tournament_type}\n"
                            f"❌ All slots are currently full.\n"
                            f"Please contact admin for assistance."
                        )
                        send_telegram_message(user_id, user_message)
                else:
                    logger.warning(f"Could not extract user_id from payment data: {payment_data}")
                
                logger.info(f"Payment processed: ₹{amount} for tournament ₹{tournament_type}")
                
                return jsonify({'status': 'success', 'message': 'Payment processed'}), 200
            else:
                logger.warning(f"Payment not processed: tournament_type={tournament_type}, status={status}")
        
        return jsonify({'status': 'ignored', 'message': 'Event not handled'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/payment-success', methods=['GET'])
def payment_success():
    """Handle payment success redirect"""
    payment_id = request.args.get('razorpay_payment_id')
    payment_link_id = request.args.get('razorpay_payment_link_id')
    
    if payment_id and payment_link_id:
        # Send success message to admin
        message = (
            f"✅ <b>Payment Success Redirect</b>\n\n"
            f"🆔 Payment ID: {payment_id}\n"
            f"🔗 Link ID: {payment_link_id}\n"
            f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        
        send_telegram_message(ADMIN_ID, message)
        
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Successful</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f0f8ff;
                }
                .success-container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    max-width: 400px;
                    margin: 0 auto;
                }
                .success-icon {
                    font-size: 60px;
                    color: #28a745;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #28a745;
                    margin-bottom: 20px;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                }
                .btn {
                    background-color: #007bff;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="success-container">
                <div class="success-icon">✅</div>
                <h1>Payment Successful!</h1>
                <p>Your payment has been processed successfully. Your tournament registration is now pending admin approval.</p>
                <p><strong>You will receive a notification in the bot within a few minutes once your registration is approved.</strong></p>
                <p>Please return to the Telegram bot to check your registration status.</p>
                <a href="https://t.me/eFootball_Tournamentsbot" class="btn">Return to Bot</a>
            </div>
        </body>
        </html>
        """
    
    return "Payment information not found", 400

@app.route('/trigger-update', methods=['POST'])
def trigger_update():
    """Manual trigger for testing"""
    try:
        data = request.get_json() or {}
        message = data.get('message', 'Test message from gateway')
        
        success = send_telegram_message(ADMIN_ID, f"🔧 <b>Manual Trigger</b>\n\n{message}")
        
        if success:
            return jsonify({'status': 'success', 'message': 'Message sent'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send message'}), 500
            
    except Exception as e:
        logger.error(f"Error in trigger update: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get basic statistics"""
    return jsonify({
        'status': 'active',
        'uptime': 'Running',
        'endpoints': [
            '/health',
            '/payment-webhook',
            '/payment-success',
            '/trigger-update',
            '/stats'
        ],
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/pending-payments', methods=['GET'])
def get_pending_payments():
    """Get pending payments for bot processing"""
    global pending_payments
    
    # Return and clear pending payments
    payments = pending_payments.copy()
    pending_payments.clear()
    
    return jsonify({
        'status': 'success',
        'payments': payments,
        'count': len(payments)
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
from flask import Flask, request, jsonify
import os
import asyncio
import logging
from datetime import datetime
import requests
import hmac
import hashlib
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '1181844922'))
PAYMENT_GATEWAY_SECRET = os.getenv('PAYMENT_GATEWAY_SECRET')

# Import bot functions (this would need to be restructured in a real implementation)
# For now, we'll create a simple notification system

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
        if not verify_razorpay_signature(payload, signature, PAYMENT_GATEWAY_SECRET):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Parse the webhook data
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({'error': 'No data received'}), 400
        
        event = webhook_data.get('event')
        payment_data = webhook_data.get('payload', {}).get('payment_link', {})
        
        logger.info(f"Received webhook event: {event}")
        
        if event == 'payment_link.paid':
            # Extract payment information
            payment_link_id = payment_data.get('id')
            amount = payment_data.get('amount', 0) // 100  # Convert from paise to rupees
            status = payment_data.get('status')
            
            # Determine tournament type based on amount
            tournament_type = None
            if amount == 15:
                tournament_type = 15
            elif amount == 30:
                tournament_type = 30
            elif amount == 50:
                tournament_type = 50
            
            if tournament_type and status == 'paid':
                # Notify admin about successful payment
                message = (
                    f"💳 <b>Payment Received!</b>\n\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"🏆 Tournament: ₹{tournament_type}\n"
                    f"🆔 Payment ID: {payment_link_id}\n"
                    f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"Please check the bot for registration approval."
                )
                
                send_telegram_message(ADMIN_ID, message)
                
                logger.info(f"Payment processed: ₹{amount} for tournament ₹{tournament_type}")
                
                return jsonify({'status': 'success', 'message': 'Payment processed'}), 200
        
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
                <p>You will receive a notification in the bot once your registration is approved.</p>
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
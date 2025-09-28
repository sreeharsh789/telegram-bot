# eFootball Tournament Bot

A comprehensive Telegram bot for managing eFootball tournaments with integrated payment processing.

## Features

- **Multiple Tournament Types**: ₹15, ₹30, and ₹50 entry fees
- **Secure Payment Processing**: Integrated with Razorpay payment gateway
- **Admin Approval System**: Manual verification of registrations
- **Slot Management**: Automatic slot assignment and group updates
- **Cooldown System**: 10-minute cooldown between registrations
- **First-time User Flow**: Special onboarding for new users
- **Webhook Integration**: Real-time payment verification

## Tournament Structure

| Entry Fee | Prize | Slots |
|-----------|-------|-------|
| ₹15       | ₹25   | 2     |
| ₹30       | ₹50   | 2     |
| ₹50       | ₹80   | 2     |

## Setup Instructions

### 1. Environment Variables

Set the following environment variables in your Render dashboard:

```bash
TELEGRAM_TOKEN=your_bot_token
ADMIN_ID=your_telegram_user_id
GROUP_CHAT_ID=your_group_chat_id
PAYMENT_GATEWAY_KEY=your_razorpay_key_id
PAYMENT_GATEWAY_SECRET=your_razorpay_key_secret
BOT_USERNAME=@your_bot_username
```

### 2. Razorpay Setup

1. Create a Razorpay account at https://razorpay.com
2. Get your Key ID and Key Secret from the dashboard
3. Configure webhook URL: `https://your-app.onrender.com/payment-webhook`
4. Enable the following webhook events:
   - `payment_link.paid`

### 3. Telegram Bot Setup

1. Create a bot using @BotFather
2. Get the bot token
3. Add the bot to your tournament group
4. Make the bot an admin in the group

### 4. Deployment

1. Connect your GitHub repository to Render
2. Set the environment variables
3. Deploy the service

## Bot Commands

- `/start` - Welcome message and group link
- `/register` - Start tournament registration

## API Endpoints

- `GET /health` - Health check
- `POST /payment-webhook` - Payment gateway webhook
- `GET /payment-success` - Payment success redirect
- `POST /trigger-update` - Manual testing trigger
- `GET /stats` - Service statistics

## File Structure

```
├── bot.py              # Main bot logic
├── gateway.py          # Flask webhook server
├── requirements.txt    # Python dependencies
├── start.sh           # Startup script
├── render.yaml        # Render deployment config
├── Procfile          # Process configuration
└── README.md         # Documentation
```

## Usage Flow

1. User joins the group and uses `/register`
2. Bot shows tournament options
3. User selects tournament and gets payment link
4. User completes payment via Razorpay
5. Payment webhook notifies the bot
6. Admin receives approval request
7. Admin approves/declines registration
8. User gets assigned to tournament slot
9. Group gets updated with current slots

## Security Features

- Webhook signature verification
- User ID validation for callbacks
- Cooldown system to prevent spam
- Admin-only approval system
- Secure payment processing

## Support

For issues or questions, contact the bot administrator.
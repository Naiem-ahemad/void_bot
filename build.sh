#!/bin/bash

echo "Setting up Telegram webhook for Netlify..."

# Replace with your actual Netlify function URL
WEBHOOK_URL="https://your-site.netlify.app/.netlify/functions/telegram_bot"
TELEGRAM_TOKEN="7739864646:AAEUb0M6w0pwQNPbwxFN9Kg7Up0jH_ytRyU"

curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook" \
     -d "url=$WEBHOOK_URL"

echo "Webhook set to $WEBHOOK_URL"

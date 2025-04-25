# Bittensor Subnet Alerts Bot

A Discord bot that monitors Bittensor subnet prices and sends alerts when prices reach specified targets. The bot supports multiple alerts per subnet, price history tracking, and immediate notifications.

## Features

- **Price Monitoring**: Continuously monitors all Bittensor subnets for price changes
- **Multiple Alerts**: Set multiple price alerts for the same subnet
- **Price History**: Track and view alert history for all subnets
- **Immediate Alerts**: Get instant notifications when prices match your target
- **User Tagging**: Get mentioned in all alert-related messages
- **Flexible Alert Types**: Set alerts for both price increases and decreases
- **Detailed Information**: View current prices, market caps, and subnet details

## Commands

### Price Commands
- `!price <subnet_id>` - Get current price and details for a specific subnet

### Alert Commands
- `!setalert <subnet_id> <target_price>` - Set a price alert for a subnet
  - Example: `!setalert 0 1.0` - Alert when subnet 0 reaches 1.0 τ
  - You can set multiple alerts for the same subnet
  - Alerts trigger immediately if the current price matches your target
- `!myalerts` - List all your active price alerts
- `!removealert <subnet_id>` - Remove all your alerts for a specific subnet
- `!alert_history [subnet_id]` - View alert history (optionally filtered by subnet)

## Alert Types

The bot supports two types of alerts:
1. **Price Increase Alerts**: Trigger when price rises to or above your target
2. **Price Decrease Alerts**: Trigger when price falls to or below your target

The alert type is automatically determined based on your target price relative to the current price.

## Alert History

All triggered alerts are saved to history, including:
- Target price
- Initial price
- Triggered price
- Direction (increase/decrease)
- Timestamp
- User who set the alert

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bittensor-subnet-alerts.git
cd bittensor-subnet-alerts
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Discord bot token and channel ID:
```env
DISCORD_TOKEN=your_discord_bot_token
CHANNEL_ID=your_alert_channel_id
```

4. Run the bot:
```bash
python bittensor_alerter.py
```

## Requirements

- Python 3.7+
- discord.py
- bittensor
- python-dotenv
- schedule

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
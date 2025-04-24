# Bittensor Subnet Alerts

A Discord bot that monitors Bittensor subnet prices and sends alerts when prices reach specified thresholds. This bot allows users to set custom price alerts for any Bittensor subnet and receive notifications in a Discord channel.

## Features

- Set price alerts for any Bittensor subnet
- Receive instant notifications when price targets are reached
- View current subnet prices
- List your active alerts
- View alert history
- User-specific alert management

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Bittensor CLI installed
- Discord channel ID where alerts will be sent

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Bittensor-Subnet-Alerts.git
cd Bittensor-Subnet-Alerts
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token_here
CHANNEL_ID=your_channel_id_here
```

## Usage

### Bot Commands

- `!setalert <subnet_id> <target_price>` - Set a price alert for a specific subnet
  Example: `!setalert 0 1.5`

- `!myalerts` - List all your active price alerts

- `!removealert <subnet_id>` - Remove an alert for a specific subnet
  Example: `!removealert 0`

- `!price <subnet_id>` - Get current price of a specific subnet
  Example: `!price 0`

- `!alert_history [subnet_id]` - View alert history (optional subnet_id parameter)
  Example: `!alert_history` or `!alert_history 0`

### Setting Up the Bot

1. Create a Discord bot and get its token:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

2. Get your channel ID:
   - In Discord, enable Developer Mode (Settings > Advanced > Developer Mode)
   - Right-click on the channel and select "Copy ID"

3. Update the `.env` file with your bot token and channel ID

4. Run the bot:
```bash
python bittensor_alerter.py
```

## Alert System

- The bot checks subnet prices every minute
- Alerts are triggered when the current price reaches or exceeds the target price
- Alerts are user-specific and can be managed individually
- Alert history is maintained for reference

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 
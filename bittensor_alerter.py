import os
import discord
from discord.ext import commands
import bittensor as bt
from dotenv import load_dotenv
import schedule
import time
import asyncio
from datetime import datetime
from typing import Dict, List
import json
import subprocess
import re

# Load environment variables
load_dotenv()

# Discord bot setup
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Bittensor
bt.logging.set_trace(True)
config = bt.subtensor.config()
subtensor = bt.subtensor(config=config)

# File to store alerts
ALERTS_FILE = 'price_alerts.json'
HISTORY_FILE = 'alert_history.json'

# Store price alerts: {subnet_uid: {user_id: target_price}}
price_alerts: Dict[int, Dict[int, float]] = {}

# Store alert history: {subnet_uid: [{user_id: int, target_price: float, triggered_price: float, timestamp: str}]}
alert_history: Dict[int, List[Dict]] = {}

def load_alerts():
    """Load alerts from JSON file"""
    global price_alerts, alert_history
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                # Convert string keys back to integers
                data = json.load(f)
                price_alerts = {int(k): {int(u): float(p) for u, p in v.items()} 
                              for k, v in data.items()}
            print(f"Loaded {len(price_alerts)} alerts from {ALERTS_FILE}")
            
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                # Convert string keys back to integers
                data = json.load(f)
                alert_history = {int(k): v for k, v in data.items()}
            print(f"Loaded alert history from {HISTORY_FILE}")
    except Exception as e:
        print(f"Error loading alerts/history: {e}")
        price_alerts = {}
        alert_history = {}

def save_alerts():
    """Save alerts and history to JSON files"""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(price_alerts, f)
        print(f"Saved {len(price_alerts)} alerts to {ALERTS_FILE}")
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(alert_history, f)
        print(f"Saved alert history to {HISTORY_FILE}")
    except Exception as e:
        print(f"Error saving alerts/history: {e}")

async def check_subnet_prices():
    """Check subnet prices and send alerts if target prices are reached"""
    try:
        print(f"Starting price check. Active alerts: {price_alerts}")
        
        # Get all subnets
        subnets = list(range(101))  # Check all 101 subnets
        
        for subnet_uid in subnets:
            if subnet_uid not in price_alerts:
                continue
                
            try:
                print(f"Checking subnet {subnet_uid}...")
                # Get subnet info
                subnet_info = subtensor.subnet(subnet_uid)
                if not subnet_info:
                    print(f"Subnet {subnet_uid} does not exist")
                    continue
                    
                current_price = float(subnet_info.price)
                print(f"Subnet {subnet_uid} current price: {current_price}")
                
                # Check alerts for this subnet
                for user_id, target_price in price_alerts[subnet_uid].items():
                    print(f"Checking alert for user {user_id}: target {target_price}, current {current_price}")
                    if current_price >= target_price:
                        print(f"Alert triggered for subnet {subnet_uid}!")
                        channel = bot.get_channel(CHANNEL_ID)
                        if channel:
                            user = await bot.fetch_user(user_id)
                            await channel.send(
                                f"🚨 **Price Alert for Subnet {subnet_uid}** 🚨\n"
                                f"Target Price: {target_price:.4f} τ\n"
                                f"Current Price: {current_price:.4f} τ\n"
                                f"Alert set by: {user.mention}"
                            )
                            
                            # Add to alert history
                            if subnet_uid not in alert_history:
                                alert_history[subnet_uid] = []
                            alert_history[subnet_uid].append({
                                'user_id': user_id,
                                'target_price': target_price,
                                'triggered_price': current_price,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            # Remove the alert after triggering
                            del price_alerts[subnet_uid][user_id]
                            if not price_alerts[subnet_uid]:
                                del price_alerts[subnet_uid]
                            # Save alerts and history after removing triggered ones
                            save_alerts()
                            print(f"Alert removed and saved for subnet {subnet_uid}")
                        else:
                            print(f"Could not find channel {CHANNEL_ID}")
                    else:
                        print(f"Price not reached for subnet {subnet_uid}: {current_price} < {target_price}")
            except Exception as e:
                print(f"Error checking subnet {subnet_uid}: {e}")
                continue
            
    except Exception as e:
        print(f"Error checking subnet prices: {e}")

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    # Load saved alerts when bot starts
    load_alerts()
    print(f"Loaded alerts: {price_alerts}")
    
    # Schedule price checks every 1 minute
    schedule.every(1).minutes.do(lambda: asyncio.create_task(check_subnet_prices()))
    
    # Run the scheduler in the background
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

@bot.command(name='setalert')
async def set_alert(ctx, subnet_uid: int, target_price: float):
    """Set a price alert for a specific subnet"""
    try:
        print(f"Setting alert for subnet {subnet_uid} with target price {target_price}")
        # Validate subnet exists
        try:
            subnet_info = subtensor.subnet(subnet_uid)
            if not subnet_info:
                await ctx.send(f"❌ Subnet {subnet_uid} does not exist!")
                return
            current_price = float(subnet_info.price)
            print(f"Current price for subnet {subnet_uid}: {current_price}")
        except Exception as e:
            print(f"Error validating subnet: {e}")
            await ctx.send(f"❌ Subnet {subnet_uid} does not exist!")
            return
            
        # Initialize alerts for this subnet if needed
        if subnet_uid not in price_alerts:
            price_alerts[subnet_uid] = {}
            
        # Add or update alert
        price_alerts[subnet_uid][ctx.author.id] = target_price
        # Save alerts after adding new one
        save_alerts()
        print(f"Alert saved: {price_alerts}")
        
        await ctx.send(
            f"✅ Alert set for Subnet {subnet_uid}!\n"
            f"Current Price: {current_price:.4f} τ\n"
            f"Target Price: {target_price:.4f} τ\n"
            f"You will be notified when the price reaches or exceeds this value."
        )
    except Exception as e:
        print(f"Error setting alert: {e}")
        await ctx.send(f"❌ Error setting alert: {e}")

@bot.command(name='myalerts')
@commands.cooldown(1, 2, commands.BucketType.user)  # 5 second cooldown per user
async def list_alerts(ctx):
    """List all alerts set by the user"""
    try:
        user_alerts = []
        for subnet_uid, alerts in price_alerts.items():
            if ctx.author.id in alerts:
                # Get subnet info for the name
                subnet_info = subtensor.subnet(subnet_uid)
                subnet_name = subnet_info.subnet_name if subnet_info else "Unknown"
                user_alerts.append(f"Subnet {subnet_uid} ({subnet_name}): {alerts[ctx.author.id]:.4f} τ")
        
        if not user_alerts:
            await ctx.send(f"{ctx.author.mention} You have no active price alerts.")
        else:
            message = f"{ctx.author.mention} **Your Active Price Alerts**\n\n" + "\n".join(user_alerts)
            await ctx.send(message)
    except commands.CommandOnCooldown:
        # Don't send any message if command is on cooldown
        return
    except Exception as e:
        await ctx.send(f"❌ {ctx.author.mention} Error listing alerts: {e}")

@bot.command(name='removealert')
async def remove_alert(ctx, subnet_uid: int):
    """Remove a price alert for a specific subnet"""
    try:
        if subnet_uid in price_alerts and ctx.author.id in price_alerts[subnet_uid]:
            del price_alerts[subnet_uid][ctx.author.id]
            if not price_alerts[subnet_uid]:
                del price_alerts[subnet_uid]
            # Save alerts after removing one
            save_alerts()
            await ctx.send(f"✅ Alert removed for Subnet {subnet_uid}")
        else:
            await ctx.send(f"❌ No active alert found for Subnet {subnet_uid}")
    except Exception as e:
        await ctx.send(f"❌ Error removing alert: {e}")

@bot.command(name='alert_history')
async def show_alert_history(ctx, subnet_uid: int = None):
    """Show alert history for a specific subnet or all subnets"""
    try:
        if not alert_history:
            await ctx.send("No alert history available yet.")
            return
            
        if subnet_uid is not None:
            # Show history for specific subnet
            if subnet_uid not in alert_history:
                await ctx.send(f"No alert history found for Subnet {subnet_uid}.")
                return
                
            history = alert_history[subnet_uid]
            message = f"**Alert History for Subnet {subnet_uid}**\n\n"
            for alert in history:
                user = await bot.fetch_user(alert['user_id'])
                timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                message += (
                    f"• {timestamp} - {user.mention}\n"
                    f"  Target: {alert['target_price']:.4f} τ | "
                    f"Triggered at: {alert['triggered_price']:.4f} τ\n"
                )
        else:
            # Show history for all subnets
            message = "**Alert History for All Subnets**\n\n"
            for subnet_id, history in alert_history.items():
                message += f"**Subnet {subnet_id}**\n"
                for alert in history:
                    user = await bot.fetch_user(alert['user_id'])
                    timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    message += (
                        f"• {timestamp} - {user.mention}\n"
                        f"  Target: {alert['target_price']:.4f} τ | "
                        f"Triggered at: {alert['triggered_price']:.4f} τ\n"
                    )
                message += "\n"
        
        # Split message if too long
        if len(message) > 2000:
            parts = [message[i:i+2000] for i in range(0, len(message), 2000)]
            for part in parts:
                await ctx.send(part)
                await asyncio.sleep(0.5)
        else:
            await ctx.send(message)
            
    except Exception as e:
        print(f"Error showing alert history: {e}")
        await ctx.send(f"❌ Error showing alert history: {e}")

@bot.command(name='price')
async def get_subnet_price(ctx, subnet_uid: int):
    """Get current price of a specific subnet"""
    try:
        print(f"Getting price for subnet {subnet_uid} (requested by {ctx.author.name})")
        # Get subnet info
        subnet_info = subtensor.subnet(subnet_uid)
        if not subnet_info:
            await ctx.send(f"❌ {ctx.author.mention} Subnet {subnet_uid} does not exist!")
            return
            
        current_price = float(subnet_info.price)
        subnet_name = subnet_info.subnet_name
        
        # Format the message
        message = (
            f"**Subnet {subnet_uid} ({subnet_name})**\n"
            f"Current Price: {current_price:.4f} τ\n"
            f"Requested by: {ctx.author.mention}"
        )
        
        await ctx.send(message)
    except Exception as e:
        print(f"Error getting subnet price: {e}")
        await ctx.send(f"❌ {ctx.author.mention} Error getting price for subnet {subnet_uid}: {e}")

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN) 
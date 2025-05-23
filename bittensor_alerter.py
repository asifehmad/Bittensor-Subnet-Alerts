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
ALLOWED_SERVER_ID = int(os.getenv('ALLOWED_SERVER_ID'))
COMMAND_CHANNEL_ID = int(os.getenv('COMMAND_CHANNEL_ID'))

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True  # Enable DM messages
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
        # Load price alerts
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                data = json.load(f)
                price_alerts = {}
                for subnet_id, alerts in data.items():
                    price_alerts[int(subnet_id)] = {}
                    for user_id, user_alerts in alerts.items():
                        price_alerts[int(subnet_id)][int(user_id)] = []
                        if isinstance(user_alerts, list):
                            for alert in user_alerts:
                                price_alerts[int(subnet_id)][int(user_id)].append({
                                    'target_price': float(alert['target_price']),
                                    'initial_price': float(alert['initial_price'])
                                })
                        else:
                            # Handle old format
                            price_alerts[int(subnet_id)][int(user_id)].append({
                                'target_price': float(user_alerts),
                                'initial_price': float(user_alerts)
                            })
            print(f"Loaded {len(price_alerts)} alerts from {ALERTS_FILE}")
            print(f"Alert details: {price_alerts}")
        else:
            print(f"No existing alerts file found at {ALERTS_FILE}")
            
        # Load alert history
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                alert_history = {}
                for subnet_id, history in data.items():
                    alert_history[int(subnet_id)] = []
                    for alert in history:
                        alert_history[int(subnet_id)].append({
                            'user_id': int(alert['user_id']),
                            'target_price': float(alert['target_price']),
                            'initial_price': float(alert['initial_price']),
                            'triggered_price': float(alert['triggered_price']),
                            'direction': alert['direction'],
                            'timestamp': alert['timestamp']
                        })
            print(f"Loaded alert history from {HISTORY_FILE}")
            print(f"History details: {alert_history}")
        else:
            print(f"No existing history file found at {HISTORY_FILE}")
            
    except Exception as e:
        print(f"Error loading alerts/history: {e}")
        print(f"Raw data: {data if 'data' in locals() else 'No data loaded'}")
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
                for user_id, user_alerts in price_alerts[subnet_uid].items():
                    # Convert to list if it's not already (for backward compatibility)
                    if not isinstance(user_alerts, list):
                        user_alerts = [user_alerts]
                    
                    # Track which alerts to remove
                    alerts_to_remove = []
                    
                    for alert_index, alert_data in enumerate(user_alerts):
                        if isinstance(alert_data, dict):
                            target_price = alert_data['target_price']
                            initial_price = alert_data['initial_price']
                        else:
                            # Handle old format
                            target_price = alert_data
                            initial_price = target_price
                        
                        print(f"Checking alert for user {user_id}: target {target_price}, current {current_price}")
                        
                        # Determine if we're watching for price increase or decrease
                        is_watching_increase = target_price > initial_price
                        
                        # Check if price has crossed the target or equals it
                        if (is_watching_increase and current_price >= target_price) or \
                           (not is_watching_increase and current_price <= target_price) or \
                           (current_price == target_price):
                            print(f"Alert triggered for subnet {subnet_uid}!")
                            
                            try:
                                user = await bot.fetch_user(user_id)
                                direction = "increased" if is_watching_increase else "decreased"
                                if current_price == target_price:
                                    direction = "matched"
                                
                                # Send alert via DM
                                await user.send(
                                    f"🚨 **Price Alert for Subnet {subnet_uid}** 🚨\n"
                                    f"Target Price: {target_price:.4f} τ\n"
                                    f"Current Price: {current_price:.4f} τ\n"
                                    f"Price has {direction} from {initial_price:.4f} τ"
                                )
                                
                                # Add to alert history
                                if subnet_uid not in alert_history:
                                    alert_history[subnet_uid] = []
                                alert_history[subnet_uid].append({
                                    'user_id': user_id,
                                    'target_price': target_price,
                                    'initial_price': initial_price,
                                    'triggered_price': current_price,
                                    'direction': direction,
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                # Mark this alert for removal
                                alerts_to_remove.append(alert_index)
                            except Exception as e:
                                print(f"Error sending DM to user {user_id}: {e}")
                                continue
                        else:
                            print(f"Price not reached for subnet {subnet_uid}: {current_price} {'<' if is_watching_increase else '>'} {target_price}")
                    
                    # Remove triggered alerts in reverse order to maintain indices
                    for index in sorted(alerts_to_remove, reverse=True):
                        del price_alerts[subnet_uid][user_id][index]
                    
                    # If no alerts left for this user in this subnet, clean up
                    if not price_alerts[subnet_uid][user_id]:
                        del price_alerts[subnet_uid][user_id]
                        if not price_alerts[subnet_uid]:
                            del price_alerts[subnet_uid]
                    
                    # Save alerts and history after processing all alerts
                    save_alerts()
            except Exception as e:
                print(f"Error checking subnet {subnet_uid}: {e}")
                continue
            
    except Exception as e:
        print(f"Error checking subnet prices: {e}")

def is_command_channel():
    """Check if the command is being used in the designated command channel"""
    async def predicate(ctx):
        if ctx.guild is None:  # If command is used in DMs
            return False
        return ctx.guild.id == ALLOWED_SERVER_ID and ctx.channel.id == COMMAND_CHANNEL_ID
    return commands.check(predicate)

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

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        if ctx.guild is None:  # If in DMs
            return  # Don't send message in DMs
        elif ctx.guild.id != ALLOWED_SERVER_ID:
            await ctx.send("❌ This bot can only be used in the specified server.")
        elif ctx.channel.id != COMMAND_CHANNEL_ID:
            await ctx.send(f"❌ Commands can only be used in the designated command channel.")
        else:
            await ctx.send("❌ An error occurred while processing your command.")
    else:
        print(f"Error: {error}")

@bot.command(name='setalert')
@is_command_channel()
async def set_alert(ctx, subnet_uid: int, target_price: float):
    """Set a price alert for a specific subnet"""
    try:
        print(f"Setting alert for subnet {subnet_uid} with target price {target_price}")
        # Validate subnet exists
        try:
            # First check if subnet exists
            subnet_info = subtensor.subnet(subnet_uid)
            if subnet_info is None:
                print(f"Subnet {subnet_uid} returned None")
                await ctx.send(f"❌ {ctx.author.mention} Subnet {subnet_uid} does not exist!")
                return
                
            # Try to get the price to verify subnet is active
            try:
                current_price = float(subnet_info.price)
                print(f"Current price for subnet {subnet_uid}: {current_price}")
            except Exception as e:
                print(f"Error getting price for subnet {subnet_uid}: {e}")
                await ctx.send(f"❌ {ctx.author.mention} Could not get price for subnet {subnet_uid}. It might be inactive.")
                return
            
            # If target price equals current price, send alert immediately via DM
            if target_price == current_price:
                try:
                    await ctx.author.send(
                        f"🚨 **Price Alert for Subnet {subnet_uid}** 🚨\n"
                        f"Target Price: {target_price:.4f} τ\n"
                        f"Current Price: {current_price:.4f} τ\n"
                        f"Price matched target price immediately!"
                    )
                    
                    # Add to alert history
                    if subnet_uid not in alert_history:
                        alert_history[subnet_uid] = []
                    alert_history[subnet_uid].append({
                        'user_id': ctx.author.id,
                        'target_price': target_price,
                        'initial_price': current_price,
                        'triggered_price': current_price,
                        'direction': 'matched',
                        'timestamp': datetime.now().isoformat()
                    })
                    save_alerts()  # Save the history
                except Exception as e:
                    print(f"Error sending DM to user: {e}")
                    await ctx.send(f"❌ {ctx.author.mention} I couldn't send you a DM. Please check your privacy settings.")
                return
                    
        except Exception as e:
            print(f"Error validating subnet {subnet_uid}: {e}")
            await ctx.send(f"❌ {ctx.author.mention} Error validating subnet {subnet_uid}: {str(e)}")
            return
            
        # Initialize alerts for this subnet if needed
        if subnet_uid not in price_alerts:
            price_alerts[subnet_uid] = {}
            
        # Initialize user's alerts for this subnet if needed
        if ctx.author.id not in price_alerts[subnet_uid]:
            price_alerts[subnet_uid][ctx.author.id] = []
            
        # Add new alert to user's alerts for this subnet
        price_alerts[subnet_uid][ctx.author.id].append({
            'target_price': target_price,
            'initial_price': current_price
        })
        
        # Save alerts after adding new one
        save_alerts()
        print(f"Alert saved: {price_alerts}")
        
        # Determine alert type
        alert_type = "increase" if target_price > current_price else "decrease"
        
        await ctx.send(
            f"✅ {ctx.author.mention} Alert set for Subnet {subnet_uid}!\n"
            f"Current Price: {current_price:.4f} τ\n"
            f"Target Price: {target_price:.4f} τ\n"
            f"Alert Type: Price {alert_type}\n"
            f"You will receive a DM when the price {alert_type}s to this value."
        )
    except Exception as e:
        print(f"Error setting alert: {e}")
        await ctx.send(f"❌ {ctx.author.mention} Error setting alert: {e}")

@bot.command(name='myalerts')
@is_command_channel()
async def list_alerts(ctx):
    """List all alerts set by the user"""
    try:
        user_alerts = []
        for subnet_uid, alerts in price_alerts.items():
            if ctx.author.id in alerts:
                # Get subnet info for the name
                subnet_info = subtensor.subnet(subnet_uid)
                subnet_name = subnet_info.subnet_name if subnet_info else "Unknown"
                
                # Get all alerts for this subnet
                subnet_alerts = []
                for alert_data in alerts[ctx.author.id]:
                    if isinstance(alert_data, dict):
                        target_price = alert_data['target_price']
                        initial_price = alert_data['initial_price']
                    else:
                        # Handle old format
                        target_price = alert_data
                        initial_price = target_price
                    
                    alert_type = "increase" if target_price > initial_price else "decrease"
                    
                    subnet_alerts.append(
                        f"  - Target: {target_price:.4f} τ\n"
                        f"    Initial: {initial_price:.4f} τ\n"
                        f"    Type: Price {alert_type}"
                    )
                
                if subnet_alerts:
                    user_alerts.append(
                        f"Subnet {subnet_uid} ({subnet_name}):\n" + "\n".join(subnet_alerts)
                    )
        
        if not user_alerts:
            await ctx.send(f"{ctx.author.mention} You have no active price alerts.")
        else:
            message = f"{ctx.author.mention} **Your Active Price Alerts**\n\n" + "\n\n".join(user_alerts)
            
            # Split message if too long
            if len(message) > 2000:
                parts = [message[i:i+2000] for i in range(0, len(message), 2000)]
                for part in parts:
                    await ctx.send(part)
                    await asyncio.sleep(0.5)  # Small delay between messages
            else:
                await ctx.send(message)
    except Exception as e:
        print(f"Error listing alerts: {e}")
        await ctx.send(f"❌ {ctx.author.mention} Error listing alerts: {e}")

@bot.command(name='removealert')
@is_command_channel()
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
@is_command_channel()
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
                    f"Initial: {alert['initial_price']:.4f} τ | "
                    f"Triggered at: {alert['triggered_price']:.4f} τ\n"
                    f"Direction: {alert['direction']}\n"
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
                        f"Initial: {alert['initial_price']:.4f} τ | "
                        f"Triggered at: {alert['triggered_price']:.4f} τ\n"
                        f"Direction: {alert['direction']}\n"
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
@is_command_channel()
async def get_subnet_price(ctx, subnet_uid: int):
    """Get current price of a specific subnet"""
    try:
        print(f"Getting price for subnet {subnet_uid} (requested by {ctx.author.name})")
        # Get subnet info
        subnet_info = subtensor.subnet(subnet_uid)
        if subnet_info is None:
            print(f"Subnet {subnet_uid} returned None")
            await ctx.send(f"❌ {ctx.author.mention} Subnet {subnet_uid} does not exist!")
            return
            
        try:
            current_price = float(subnet_info.price)
            subnet_name = subnet_info.subnet_name
            print(f"Successfully got price for subnet {subnet_uid}: {current_price}")
        except Exception as e:
            print(f"Error getting price for subnet {subnet_uid}: {e}")
            await ctx.send(f"❌ {ctx.author.mention} Could not get price for subnet {subnet_uid}. It might be inactive.")
            return
            
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
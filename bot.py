import discord
import os
import json
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from discord.ext import commands, tasks

# --- Custom Imports ---
from leetcode_buddy import get_user_stats
from website import start_website
from commands import UserCommands, welcome_user
from help_system import HelpSystem
from ai_helper import get_hint

# --- Configuration ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True # Required to read commands
intents.members = True         # Required for welcome messages
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- Database Management ---
DB_FILE = 'user_data.json'
users_db = {}

def load_user_data():
    global users_db
    try:
        with open(DB_FILE, 'r') as f:
            users_db = json.load(f)
    except FileNotFoundError:
        users_db = {}

def save_user_data():
    with open(DB_FILE, 'w') as f:
        json.dump(users_db, f)

# --- Core Logic: Daily Checker ---
async def run_check_logic(target_channel):
    """
    Checks status for all users, updates the database (for the website),
    and sends a report to Discord.
    """
    if not users_db:
        await target_channel.send("⚠️ No users registered in the database.")
        return

    # Notify users check is starting
    status_msg = await target_channel.send("🔄 **Syncing Data & Checking Daily Status...**")
    
    incomplete_users = []
    
    for discord_id, user_data in users_db.items():
        # Handle backward compatibility (str -> dict)
        if isinstance(user_data, str):
            user_data = {'leetcode_username': user_data}
            users_db[discord_id] = user_data

        username = user_data['leetcode_username']
        
        # 1. Fetch FULL stats from LeetCode
        stats = get_user_stats(username)
        
        if stats:
            # 2. Update Database (Live sync for Website)
            users_db[discord_id]['total_solved'] = stats['total_solved']
            users_db[discord_id]['breakdown'] = stats['breakdown']
            users_db[discord_id]['last_status'] = stats['solved_today']
            
            # 3. Track incomplete users
            if not stats['solved_today']:
                incomplete_users.append(discord_id)
        else:
            print(f"⚠️ Failed to fetch stats for {username}")

    # Save updated stats to JSON
    save_user_data()
    
    # Cleanup notification
    try: await status_msg.delete()
    except: pass

    # 4. Send Report
    if incomplete_users:
        mentions = " ".join([f"<@{uid}>" for uid in incomplete_users])
        embed = discord.Embed(
            title="🚨 Daily Challenge Report", 
            description=f"The following users have **NOT** completed the daily challenge:\n\n{mentions}\n\n**Hurry up!** ⏳",
            color=0xff0000
        )
        tz = pytz.timezone('Asia/Kolkata')
        embed.set_footer(text=f"Checked at {datetime.now(tz).strftime('%I:%M %p')}")
        await target_channel.send(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ All Clear!", 
            description="🎉 Everyone has completed today's challenge! Excellent work!", 
            color=0x00ff00
        )
        await target_channel.send(embed=embed)

# --- Events ---
@bot.event
async def on_ready():
    load_user_data()
    
    # 1. Start the Website Server (Background Thread)
    start_website()
    
    # 2. Initialize Helpers
    global user_commands, help_system
    user_commands = UserCommands(users_db, save_user_data)
    help_system = HelpSystem(save_user_data)
    
    print(f"✅ Logged in as {bot.user}")
    print("✅ Website is running on port 8080")
    
    # 3. Start Scheduled Task
    if not daily_check_loop.is_running():
        daily_check_loop.start()

@bot.event
async def on_member_join(member):
    """Welcome new members"""
    channel = bot.get_channel(CHANNEL_ID)
    if channel: 
        await welcome_user(member, channel) 

@bot.event
async def on_message(message):
    """Master Router for all commands"""
    if message.author.bot: return
    
    msg = message.content
    
    # --- 1. AI Hint Command (Flexible Version) ---
    if msg.startswith('!hint'):
        # Split only ONCE to separate "!hint" from the rest of the text
        parts = msg.split(' ', 1)
        
        if len(parts) < 2:
            await message.channel.send("🧠 **Usage:** `!hint <Anything you want to ask>`\n*Example: !hint how do I solve Two Sum with a hashmap?*")
            return
        
        user_query = parts[1] # This captures "Two Sum how do I use a map?"
        
        loading = await message.channel.send("🤔 **Thinking...**")
        
        # Send the raw query to the updated AI helper
        hint = await get_hint(user_query)
        
        await loading.edit(content=f"**🤖 AI Tutor:**\n{hint}")
        return

    # --- 2. User Management Commands ---
    try:
        if msg.startswith('!register'):
            await user_commands.register_user(message)
        elif msg.startswith('!unregister'):
            await user_commands.unregister_user(message)
        elif msg == '!mystatus':
            await user_commands.show_status(message)
        elif msg == '!leaderboard':
            await user_commands.show_leaderboard(message)
        elif msg == '!progress':       
            await user_commands.show_progress(message)
        elif msg == '!stats':          
            await user_commands.show_stats(message)
        elif msg == '!help':
            await user_commands.show_help(message.channel)

        # --- 3. Help/Q&A System Commands ---
        elif msg.startswith('!ask'):
            await help_system.ask_question(message)
        elif msg.startswith('!solve'):
            await help_system.solve_question(message)
        elif msg.startswith('!code'):
            await help_system.share_code(message)
        elif msg == '!questions':
            await help_system.show_questions(message)
        elif msg == '!helpers':
            await help_system.show_helpers(message)
        elif msg == '!helpme':
            await help_system.show_help_commands(message)
            
        # --- 4. Fallback ---
        else:
            await bot.process_commands(message)
            
    except Exception as e:
        print(f"Error processing command: {e}")
        await message.channel.send("⚠️ An internal error occurred.")

# --- Admin Commands ---
@bot.command()
async def force_check(ctx):
    """Manual trigger for daily check"""
    await run_check_logic(ctx.channel)

# --- Scheduled Task ---
@tasks.loop(minutes=1)
async def daily_check_loop():
    await bot.wait_until_ready()
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    
    # Run at 9:30 PM IST
    if now.hour == 21 and now.minute == 30:
        channel = bot.get_channel(CHANNEL_ID)
        if channel: await run_check_logic(channel)

# --- Entry Point ---
if __name__ == "__main__":
    bot.run(TOKEN)
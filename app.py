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
# Updated Import: Use the new generic AI response function
from ai_helper import get_ai_response

# --- Configuration ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True          
intents.guilds = True

# Disable default help to prevent double messages
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
    if message.author.bot: 
        return
    
    msg = message.content.strip()
    
    # --- 1. AI Hint Command (Flexible Version) ---
    if msg.startswith('!hint'):
        parts = msg.split(' ', 1)
        
        if len(parts) < 2:
            await message.channel.send("🧠 **Usage:** `!hint <Anything you want to ask>`\n*Example: !hint how do I solve Two Sum with a hashmap?*")
            return
        
        user_query = parts[1]
        
        loading = await message.channel.send("🤔 **Thinking...**")
        
        # USE NEW AI HELPER
        hint = await get_ai_response(user_query)
        
        await loading.edit(content=f"**🤖 AI Tutor:**\n{hint}")
        return  # STOP HERE

    # --- 2. User Management Commands ---
    try:
        if msg.startswith('!register'):
            await user_commands.register_user(message)
            return
        elif msg.startswith('!unregister'):
            await user_commands.unregister_user(message)
            return
        elif msg == '!mystatus':
            await user_commands.show_status(message)
            return
        elif msg == '!leaderboard':
            await user_commands.show_leaderboard(message)
            return
        elif msg == '!progress':        
            await user_commands.show_progress(message)
            return
        elif msg == '!stats':            
            await user_commands.show_stats(message)
            return
        elif msg == '!help':
            await user_commands.show_help(message.channel)
            return

        # --- 3. Help/Q&A System Commands ---
        elif msg.startswith('!ask'):
            await help_system.ask_question(message)
            return
        elif msg.startswith('!solve'):
            await help_system.solve_question(message)
            return
        elif msg.startswith('!code'):
            await help_system.share_code(message)
            return
        elif msg == '!questions':
            await help_system.show_questions(message)
            return
        elif msg == '!helpers':
            await help_system.show_helpers(message)
            return
        elif msg == '!helpme':
            await help_system.show_help_commands(message)
            return
            
        # --- 4. Fallback: Standard Commands ---
        # Only if it starts with '!' and wasn't caught above
        if msg.startswith('!'):
            await bot.process_commands(message)
            return

        # --- 5. AI Chat Mode (Normal Conversation) ---
        # If it's NOT a command, and it's in the right channel or mentions the bot
        is_target_channel = (message.channel.id == CHANNEL_ID)
        is_mentioned = bot.user in message.mentions

        if is_target_channel or is_mentioned:
            # Clean the mention from the text
            clean_query = msg.replace(f'<@!{bot.user.id}>', '').strip()
            
            async with message.channel.typing():
                response = await get_ai_response(clean_query)
                await message.channel.send(response)
            
    except Exception as e:
        print(f"Error processing command: {e}")
        await message.channel.send("⚠️ An internal error occurred.")

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

# --- Admin & Utility Commands ---

@bot.command()
async def backup(ctx):
    """Sends a copy of the user database file"""
    if not os.path.exists(DB_FILE):
        await ctx.send("⚠️ No database file found yet (no users registered).")
        return
    
    try:
        await ctx.send("📦 **Here is your user data backup:**", file=discord.File(DB_FILE))
    except Exception as e:
        await ctx.send(f"❌ Error creating backup: {e}")

@bot.command()
async def force_check(ctx):
    """Manual trigger for daily check"""
    await run_check_logic(ctx.channel)

# --- Entry Point ---
if __name__ == "__main__":
    bot.run(TOKEN)

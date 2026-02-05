import discord
import os
import json
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from discord.ext import commands, tasks

# --- Custom Imports ---
# Make sure you have these files created!
from leetcode_buddy import get_user_stats
from website import start_website
from commands import UserCommands, welcome_user
from help_system import HelpSystem
from ai_helper import get_ai_response  # We renamed this to be more generic

# --- Configuration ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True          
intents.guilds = True

# Disable default help to prevent double rendering
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

# --- Events ---
@bot.event
async def on_ready():
    load_user_data()
    
    # 1. Start Website (Background Thread)
    start_website()
    
    # 2. Initialize Helpers
    global user_commands, help_system
    user_commands = UserCommands(users_db, save_user_data)
    help_system = HelpSystem(save_user_data)
    
    print(f"✅ Logged in as {bot.user}")
    
    # 3. Start Scheduled Task
    if not daily_check_loop.is_running():
        daily_check_loop.start()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_ID)
    if channel: 
        await welcome_user(member, channel) 

@bot.event
async def on_message(message):
    """
    Master Router:
    1. Ignores Bots
    2. Handles Custom Commands (!help, !register) -> STOPS
    3. Handles AI Chat (Normal text)
    """
    if message.author.bot: 
        return
    
    msg = message.content.strip()

    # --- 1. Custom Commands (Manual Handling) ---
    # We use 'return' after each await to stop the code from continuing
    
    if msg.startswith('!hint'):
        parts = msg.split(' ', 1)
        if len(parts) < 2:
            await message.channel.send("🧠 **Usage:** `!hint <question>`")
            return
        
        loading = await message.channel.send("🤔 **Thinking...**")
        response = await get_ai_response(parts[1])
        await loading.edit(content=f"**🤖 AI Tutor:**\n{response}")
        return

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
    elif msg.startswith('!ask'):
        await help_system.ask_question(message)
        return
    elif msg.startswith('!solve'):
        await help_system.solve_question(message)
        return
    elif msg == '!questions':
        await help_system.show_questions(message)
        return
    
    # --- 2. Fallback to Standard Commands ---
    # If it starts with '!' but wasn't caught above (e.g., admin commands)
    if msg.startswith('!'):
        await bot.process_commands(message)
        return

    # --- 3. AI Chat Mode (Normal Conversation) ---
    # Only reply if in the specific channel OR if the bot is mentioned
    is_target_channel = (message.channel.id == CHANNEL_ID)
    is_mentioned = bot.user in message.mentions

    if is_target_channel or is_mentioned:
        # Remove the mention from the text so the AI doesn't read "@BotName"
        clean_query = msg.replace(f'<@!{bot.user.id}>', '').strip()
        
        async with message.channel.typing():
            response = await get_ai_response(clean_query)
            await message.channel.send(response)

# --- Daily Loop (Kept the same) ---
@tasks.loop(minutes=1)
async def daily_check_loop():
    await bot.wait_until_ready()
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    if now.hour == 21 and now.minute == 30:
        channel = bot.get_channel(CHANNEL_ID)
        # Assuming run_check_logic is defined or imported (Add it back if missing)
        # await run_check_logic(channel) 
        pass 

if __name__ == "__main__":
    bot.run(TOKEN)

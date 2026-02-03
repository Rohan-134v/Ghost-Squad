import discord
import os
import json
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from discord.ext import commands, tasks

# --- Custom Imports ---
from leetcode_buddy import check
from keep_alive import keep_alive
from commands import UserCommands, welcome_user
from help_system import HelpSystem

# --- Setup & Config ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# --- Intents (CRITICAL for Welcome & Member checks) ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Required for on_member_join to work
intents.guild_messages = True
intents.guild_reactions = True

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

# --- Core Logic: Status Checker ---
async def run_check_logic(target_channel):
    """
    Reusable function to check all users and send a report 
    to the specific target_channel.
    """
    if not users_db:
        await target_channel.send("⚠️ No users registered in the database.")
        return

    # 1. Notify that check is starting (useful for manual force checks)
    status_msg = await target_channel.send("🔄 **Scanning LeetCode status for all users...**")

    incomplete_users = []
    
    # 2. Brute force check every user
    for discord_id, user_data in users_db.items():
        try:
            # Handle both string and dict formats
            leetcode_id = user_data.get('leetcode_username', user_data) if isinstance(user_data, dict) else user_data
            
            # The actual check from your library
            if not check(leetcode_id):
                incomplete_users.append(discord_id)
        except Exception as e:
            print(f"Error checking {discord_id}: {e}")
            incomplete_users.append(discord_id) # Assume incomplete if error, just to be safe

    # 3. Cleanup processing message
    try:
        await status_msg.delete()
    except:
        pass

    # 4. Generate Report
    if incomplete_users:
        mentions = " ".join([f"<@{user_id}>" for user_id in incomplete_users])
        embed = discord.Embed(
            title="🚨 Daily LeetCode Report",
            description=f"The following members have **NOT** completed today's challenge:\n\n{mentions}\n\n**Hurry up! Time is ticking!** ⏳",
            color=0xff0000 
        )
        # Add timestamp footer
        tz = pytz.timezone('Asia/Kolkata')
        embed.set_footer(text=f"Checked at {datetime.now(tz).strftime('%I:%M %p')}")
        await target_channel.send(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ All Clear!",
            description="🎉 Everyone has completed today's LeetCode challenge! Excellent work!",
            color=0x00ff00
        )
        await target_channel.send(embed=embed)

# --- Events ---
@bot.event
async def on_ready():
    load_user_data()
    
    # Initialize your custom classes
    global user_commands, help_system
    user_commands = UserCommands(users_db, save_user_data)
    help_system = HelpSystem(save_user_data)
    
    print(f'Logged in as {bot.user.name}')
    
    # Start the 1-minute loop
    if not daily_check_loop.is_running():
        daily_check_loop.start()

@bot.event
async def on_member_join(member):
    """Greets users when they join the server."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Calls your custom welcome logic
        await welcome_user(member, channel) 

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    try:
        # --- Help System Routing ---
        if message.content.startswith('!ask'):
            await help_system.ask_question(message)
            return
        elif message.content.startswith('!solve'):
            await help_system.solve_question(message)
            return
        elif message.content.startswith('!code'):
            await help_system.share_code(message)
            return
        elif message.content == '!questions':
            await help_system.show_questions(message)
            return
        elif message.content == '!helpers':
            await help_system.show_helpers(message)
            return
        elif message.content == '!helpme':
            await help_system.show_help_commands(message)
            return
        
        # --- User Management Routing ---
        elif message.content.startswith('!register'):
            await user_commands.register_user(message)
            return
        elif message.content == '!mystatus':
            await user_commands.show_status(message)
            return
        elif message.content == '!leaderboard':
            await user_commands.show_leaderboard(message)
            return
        elif message.content == '!progress':
            await user_commands.show_progress(message)
            return
        elif message.content == '!stats':
            await user_commands.show_stats(message)
            return
        elif message.content == '!unregister':
            await user_commands.unregister_user(message)
            return
        
        # --- Standard Commands (force_check, help, etc) ---
        await bot.process_commands(message)
        
    except Exception as e:
        print(f"Error in on_message: {e}")
        await message.channel.send("An error occurred. Please try again.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    if str(reaction.emoji) == '👍':
        if reaction.message.author.id != user.id:
            await help_system.add_helpful_point(user.id)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Use `!help` to see available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

# --- Commands ---

@bot.command()
async def help(ctx):
    await user_commands.show_help(ctx)

@bot.command()
async def force_check(ctx):
    """Manually triggers the daily check immediately in the current channel."""
    # This uses the same logic as the scheduled task but replies to YOU
    await run_check_logic(ctx.channel)

@bot.command()
async def status(ctx):
    """Check LeetCode daily challenge completion status for all registered users."""
    if not users_db:
        await ctx.send("No users registered yet. Use `!register <leetcode_username>` to get started.")
        return

    embed = discord.Embed(
        title="LeetCode Daily Challenge Status",
        color=0x00ff00
    )
    
    for discord_id, user_data in users_db.items():
        try:
            leetcode_id = user_data.get('leetcode_username', user_data) if isinstance(user_data, dict) else user_data
            has_solved = check(leetcode_id)
            status_text = "Completed" if has_solved else "Not Completed"
            embed.add_field(
                name=f"{leetcode_id}",
                value=f"<@{discord_id}> - {status_text}",
                inline=False
            )
        except Exception:
            embed.add_field(
                name=f"{leetcode_id}",
                value=f"<@{discord_id}> - Error checking status",
                inline=False
            )
    
    await ctx.send(embed=embed)

# --- Scheduled Task (Brute Force 1-Minute Loop) ---

@tasks.loop(minutes=1)
async def daily_check_loop():
    """Checks every minute. If time is 9:30 PM, run the report."""
    await bot.wait_until_ready()
    
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    
    # 21:30 = 9:30 PM
    if now.hour == 21 and now.minute == 30:
        print(f"[{now}] 9:30 PM Trigger - Running Daily Check")
        
        channel = bot.get_channel(CHANNEL_ID)
        # Fetch if cache missed
        if not channel:
            try:
                channel = await bot.fetch_channel(CHANNEL_ID)
            except Exception as e:
                print(f"CRITICAL: Channel {CHANNEL_ID} not found. Error: {e}")
                return
        
        await run_check_logic(channel)

@daily_check_loop.before_loop
async def before_daily_check():
    await bot.wait_until_ready()

# --- Run ---
try:
    keep_alive()
    bot.run(TOKEN)
except Exception as e:
    print(f"Bot crashed: {e}")
    import traceback
    traceback.print_exc()

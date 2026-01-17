import discord
import os
import json
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from discord.ext import commands, tasks
from leetcode_buddy import check
from keep_alive import keep_alive
from commands import UserCommands, welcome_user
from help_system import HelpSystem

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

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

@bot.event
async def on_ready():
    load_user_data()
    global user_commands, help_system
    user_commands = UserCommands(users_db, save_user_data)
    help_system = HelpSystem(save_user_data)
    print(f'Logged in as {bot.user.name}')
    if not daily_check_loop.is_running():
        daily_check_loop.start()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_ID)
    await welcome_user(member, channel)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    try:
        # Help system commands (handle first to prevent command processing)
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
        
        # Original commands
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
        
        await bot.process_commands(message)
    except Exception as e:
        print(f"Error in on_message: {e}")
        await message.channel.send("An error occurred. Please try again.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Award reputation points for helpful reactions
    if str(reaction.emoji) == '👍':
        # Get the message author (person being helped)
        message_author_id = reaction.message.author.id
        if message_author_id != user.id:  # Can't give points to yourself
            await help_system.add_helpful_point(user.id)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Use `!help` to see available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

@bot.command()
async def help(ctx):
    await user_commands.show_help(ctx)

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
            status = "Completed" if has_solved else "Not Completed"
            embed.add_field(
                name=f"{leetcode_id}",
                value=f"<@{discord_id}> - {status}",
                inline=False
            )
        except Exception:
            embed.add_field(
                name=f"{leetcode_id}",
                value=f"<@{discord_id}> - Error checking status",
                inline=False
            )
    
    await ctx.send(embed=embed)





@tasks.loop(minutes=60)
async def daily_check_loop():
    """Daily reminder for users who haven't completed their LeetCode challenge."""
    await bot.wait_until_ready()
    
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    
    if now.hour == 22:
        print("Running daily 10 PM check...")
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("Channel not found. Please check DISCORD_CHANNEL_ID in .env file.")
            return

        if not users_db:
            return

        incomplete_users = []
        
        for discord_id, user_data in users_db.items():
            try:
                leetcode_id = user_data.get('leetcode_username', user_data) if isinstance(user_data, dict) else user_data
                if not check(leetcode_id):
                    incomplete_users.append(discord_id)
            except Exception:
                incomplete_users.append(discord_id)
        
        if incomplete_users:
            mentions = " ".join([f"<@{user_id}>" for user_id in incomplete_users])
            embed = discord.Embed(
                title="LeetCode Reminder",
                description=f"The following members haven't completed today's challenge:\n{mentions}\n\nYou have 2 hours left!",
                color=0xff6b6b
            )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Excellent Work!",
                description="Everyone has completed today's LeetCode challenge! Keep up the great work!",
                color=0x51cf66
            )
            await channel.send(embed=embed)

@daily_check_loop.before_loop
async def before_daily_check():
    await bot.wait_until_ready()

try:
    keep_alive()
    bot.run(TOKEN)
except Exception as e:
    print(f"Bot crashed: {e}")
    import traceback
    traceback.print_exc()
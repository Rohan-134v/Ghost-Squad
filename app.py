"""
Ghost Squad Bot v2
Discord bot for LeetCode accountability, placement prep, and community Q&A.
"""

import discord
import os
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from discord.ext import commands, tasks

from cogs.user_commands import UserCommands
from cogs.help_system import HelpSystem
from cogs.placement_feed import PlacementFeed
from cogs.reminders import ReminderSystem
from ai_helper import get_ai_response, get_placement_post
from database import Database
from web.server import start_server

load_dotenv()

TOKEN           = os.getenv('DISCORD_TOKEN')
CHANNEL_ID      = int(os.getenv('DISCORD_CHANNEL_ID', 0))
PLACEMENT_CH_ID = int(os.getenv('PLACEMENT_CHANNEL_ID', CHANNEL_ID))
ADMIN_PASSWORD  = os.getenv('ADMIN_PASSWORD', 'ghostsquad@admin')
# Render injects PORT automatically; falls back to 8080 for local dev
ADMIN_PORT      = int(os.getenv('PORT', os.getenv('ADMIN_PORT', 8080)))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
db  = Database()

# ---------------------------------------------------------------------------
# DAILY LEETCODE CHECK LOGIC
# ---------------------------------------------------------------------------

async def run_check_logic(target_channel):
    users_db = db.get_all_users()
    if not users_db:
        await target_channel.send("No users registered yet.")
        return

    try:
        from leetcode_buddy import get_user_stats
    except ImportError:
        await target_channel.send("leetcode_buddy module not found. Check your installation.")
        return

    status_msg = await target_channel.send("Syncing LeetCode data, please wait...")
    incomplete_users = []

    for discord_id, user_data in users_db.items():
        if isinstance(user_data, str):
            user_data = {'leetcode_username': user_data}
        username = user_data.get('leetcode_username', '')
        stats = get_user_stats(username)
        if stats:
            db.update_user_stats(discord_id, stats)
            if not stats.get('solved_today'):
                incomplete_users.append(discord_id)

    try:
        await status_msg.delete()
    except Exception:
        pass

    tz = pytz.timezone('Asia/Kolkata')
    now_str = datetime.now(tz).strftime('%I:%M %p IST')

    if incomplete_users:
        mentions = " ".join([f"<@{uid}>" for uid in incomplete_users])
        embed = discord.Embed(
            title="Daily Challenge Report",
            description=(
                f"The following members have not completed today's challenge:\n\n"
                f"{mentions}\n\nGet it done before midnight."
            ),
            color=0xff4444
        )
        embed.set_footer(text=f"Checked at {now_str}")
        await target_channel.send(embed=embed)
    else:
        embed = discord.Embed(
            title="All Clear",
            description="Everyone has completed today's challenge. Good work.",
            color=0x00cc88
        )
        embed.set_footer(text=f"Checked at {now_str}")
        await target_channel.send(embed=embed)

# ---------------------------------------------------------------------------
# BOT EVENTS
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    global user_commands, help_system, placement_feed, reminder_system
    user_commands   = UserCommands(db)
    help_system     = HelpSystem(db)
    placement_feed  = PlacementFeed(db)
    reminder_system = ReminderSystem(db, bot)

    if not daily_check_loop.is_running():
        daily_check_loop.start()
    if not placement_post_loop.is_running():
        placement_post_loop.start()
    if not reminder_check_loop.is_running():
        reminder_check_loop.start()

    start_server(db, bot, ADMIN_PASSWORD, ADMIN_PORT)
    print(f"Web server running on port {ADMIN_PORT}  |  public: /   admin: /admin")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Ghost Squad grind"
        )
    )


@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=f"Welcome to Ghost Squad, {member.display_name}",
            description=(
                "We are a placement and DSA accountability community.\n\n"
                "Get started:\n"
                "- `!register <leetcode_username>` — link your LeetCode account\n"
                "- `!placement` — latest placement tips\n"
                "- `!roadmap` — full placement prep plan\n"
                "- `!help` — all available commands"
            ),
            color=0x7289da
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    msg = message.content.strip()

    try:
        # LeetCode / User Commands
        if msg.startswith('!register'):
            await user_commands.register_user(message); return
        elif msg.startswith('!unregister'):
            await user_commands.unregister_user(message); return
        elif msg == '!mystatus':
            await user_commands.show_status(message); return
        elif msg == '!leaderboard':
            await user_commands.show_leaderboard(message); return
        elif msg == '!progress':
            await user_commands.show_progress(message); return
        elif msg == '!stats':
            await user_commands.show_stats(message); return

        # Q&A Help System
        elif msg.startswith('!ask'):
            await help_system.ask_question(message); return
        elif msg.startswith('!solve'):
            await help_system.solve_question(message); return
        elif msg.startswith('!code'):
            await help_system.share_code(message); return
        elif msg == '!questions':
            await help_system.show_questions(message); return
        elif msg == '!helpers':
            await help_system.show_helpers(message); return
        elif msg == '!helpme':
            await help_system.show_help_commands(message); return

        # Placement Feed
        elif msg == '!placement':
            await placement_feed.post_tip(message.channel); return
        elif msg == '!roadmap':
            await placement_feed.post_roadmap(message.channel); return
        elif msg.startswith('!mock'):
            await placement_feed.mock_interview(message); return
        elif msg.startswith('!resume'):
            await placement_feed.resume_tip(message.channel); return

        # AI Hint
        elif msg.startswith('!hint'):
            parts = msg.split(' ', 1)
            if len(parts) < 2:
                await message.channel.send(
                    "Usage: `!hint <your question>`\n"
                    "Example: `!hint how do I solve Two Sum with a hashmap?`"
                )
                return
            loading = await message.channel.send("Thinking...")
            hint = await get_ai_response(parts[1])
            await loading.edit(content=f"**Ghost Squad AI:**\n{hint}")
            return

        # Admin Discord shortcuts
        elif msg == '!force_check':
            if message.author.guild_permissions.administrator:
                await run_check_logic(message.channel)
            else:
                await message.channel.send("This command is for admins only.")
            return

        elif msg == '!force_placement':
            if message.author.guild_permissions.administrator:
                ch = bot.get_channel(PLACEMENT_CH_ID)
                if ch:
                    tip = await get_placement_post()
                    embed = discord.Embed(
                        title="Placement Tip of the Day",
                        description=tip,
                        color=0xf39c12
                    )
                    await ch.send(embed=embed)
                    db.log_placement_post(tip)
            else:
                await message.channel.send("This command is for admins only.")
            return

        # Help
        elif msg == '!help' or msg == '!helpme':
            await show_help(message.channel); return

        # Fallback — handles !backup and any other @bot.command decorators
        if msg.startswith('!'):
            await bot.process_commands(message)
            return

        # AI chat for non-command messages in the bot channel or mentions
        is_target    = (message.channel.id == CHANNEL_ID)
        is_mentioned = bot.user in message.mentions

        if is_target or is_mentioned:
            clean = (
                msg
                .replace(f'<@{bot.user.id}>', '')
                .replace(f'<@!{bot.user.id}>', '')
                .strip()
            )
            if not clean:
                return
            async with message.channel.typing():
                response = await get_ai_response(clean)
                await message.channel.send(response)

    except Exception as e:
        print(f"Error in on_message: {e}")
        await message.channel.send("An internal error occurred. Please try again.")


async def show_help(channel):
    embed = discord.Embed(title="Ghost Squad Bot — Commands", color=0x7289da)
    embed.add_field(
        name="LeetCode Tracking",
        value=(
            "`!register <username>` — link your LeetCode account\n"
            "`!unregister` — remove your account\n"
            "`!mystatus` — your personal stats\n"
            "`!leaderboard` — top 10 members\n"
            "`!progress` — today's community completion\n"
            "`!stats` — aggregate community stats"
        ),
        inline=False
    )
    embed.add_field(
        name="Placement and Internships",
        value=(
            "`!placement` — AI placement tip on demand\n"
            "`!roadmap` — 6-month placement prep plan\n"
            "`!mock <role>` — mock interview question (e.g. `!mock SDE`)\n"
            "`!resume` — resume writing tip"
        ),
        inline=False
    )
    embed.add_field(
        name="Q&A System",
        value=(
            "`!ask <question>` — post a question\n"
            "`!solve <id>` — mark a question solved\n"
            "`!code <lang> <code>` — share formatted code\n"
            "`!questions` — view open questions\n"
            "`!helpers` — top community helpers\n"
            "`!helpme` — detailed Q&A guide"
        ),
        inline=False
    )
    embed.add_field(
        name="AI Tutor",
        value=(
            "`!hint <question>` — get a logic hint with no spoilers\n"
            "Or just chat naturally in this channel."
        ),
        inline=False
    )
    embed.set_footer(text="Ghost Squad | Admin panel at /admin")
    await channel.send(embed=embed)


# ---------------------------------------------------------------------------
# SCHEDULED TASKS
# ---------------------------------------------------------------------------

@tasks.loop(minutes=1)
async def daily_check_loop():
    await bot.wait_until_ready()
    if not db.get_setting('daily_check_enabled', True):
        return
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    schedule = db.get_setting('check_time', '21:30').split(':')
    if now.hour == int(schedule[0]) and now.minute == int(schedule[1]):
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await run_check_logic(channel)


@tasks.loop(minutes=1)
async def placement_post_loop():
    await bot.wait_until_ready()
    if not db.get_setting('placement_enabled', True):
        return
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    schedule = db.get_setting('placement_time', '10:00').split(':')
    if now.hour == int(schedule[0]) and now.minute == int(schedule[1]):
        channel = bot.get_channel(PLACEMENT_CH_ID)
        if channel:
            tip = await get_placement_post()
            embed = discord.Embed(
                title="Daily Placement and Internship Tip",
                description=tip,
                color=0xf39c12
            )
            embed.set_footer(text="Ghost Squad | Type !roadmap for the full prep plan")
            await channel.send(embed=embed)
            db.log_placement_post(tip)


@tasks.loop(seconds=30)
async def reminder_check_loop():
    await bot.wait_until_ready()
    due = db.get_due_reminders()
    for reminder in due:
        try:
            user = await bot.fetch_user(int(reminder['user_id']))
            if user:
                embed = discord.Embed(
                    title="Reminder",
                    description=reminder['message'],
                    color=0x3498db
                )
                embed.set_footer(text="Set via Ghost Squad Admin Panel")
                await user.send(embed=embed)
            db.mark_reminder_done(reminder['id'])
        except Exception as e:
            print(f"Reminder delivery error: {e}")
            db.mark_reminder_done(reminder['id'])


# ---------------------------------------------------------------------------
# ADMIN DISCORD COMMANDS
# ---------------------------------------------------------------------------

@bot.command(name='backup')
async def backup(ctx):
    """Send copies of all data files. Server administrators only."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("This command is for admins only.")
        return
    sent = 0
    for fname in ['users.json', 'questions.json', 'reminders.json',
                  'settings.json', 'placement_log.json']:
        fpath = os.path.join('data', fname)
        if os.path.exists(fpath):
            await ctx.send(f"`{fname}`:", file=discord.File(fpath))
            sent += 1
    if sent == 0:
        await ctx.send("No data files found yet.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_TOKEN is not set. Add it to your .env file.")
    else:
        bot.run(TOKEN)

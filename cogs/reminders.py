"""
cogs/reminders.py — Personal reminder system for Discord users
"""

import discord
import re
from datetime import datetime, timezone, timedelta


def parse_time(time_str: str):
    """Parse time strings like 30m, 2h, 1d into a timedelta."""
    time_str = time_str.strip().lower()
    match = re.fullmatch(r'(\d+)(m|h|d)', time_str)
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    return None


class ReminderSystem:
    def __init__(self, db, bot):
        self.db  = db
        self.bot = bot

    async def set_reminder(self, message):
        """!remindme <time> <message>  e.g. !remindme 30m Solve Two Sum"""
        parts = message.content.split(None, 2)
        if len(parts) < 3:
            await message.channel.send(
                "**Usage:** `!remindme <time> <message>`\n"
                "**Examples:**\n"
                "• `!remindme 30m Submit the assignment`\n"
                "• `!remindme 2h Practice graph problems`\n"
                "• `!remindme 1d Mock interview prep`"
            )
            return

        time_str = parts[1]
        reminder_msg = parts[2].strip()

        delta = parse_time(time_str)
        if delta is None:
            await message.channel.send(
                "❌ Invalid time format. Use `30m`, `2h`, or `1d`."
            )
            return

        fire_at = datetime.now(timezone.utc) + delta
        rid = self.db.add_reminder(str(message.author.id), reminder_msg, fire_at)

        # Human-readable time
        if delta.total_seconds() < 3600:
            time_display = f"{int(delta.total_seconds() // 60)} minute(s)"
        elif delta.total_seconds() < 86400:
            time_display = f"{int(delta.total_seconds() // 3600)} hour(s)"
        else:
            time_display = f"{int(delta.days)} day(s)"

        await message.channel.send(
            f"⏰ **Reminder set!** I'll DM you in **{time_display}**.\n"
            f"> {reminder_msg}\n"
            f"ID: `{rid}` (use `!cancelreminder {rid}` to cancel)"
        )

    async def list_reminders(self, message):
        user_id = str(message.author.id)
        reminders = self.db.get_user_reminders(user_id)

        if not reminders:
            await message.channel.send("📭 You have no active reminders. Set one with `!remindme <time> <message>`.")
            return

        embed = discord.Embed(title="⏰ Your Reminders", color=0x3498db)
        now = datetime.now(timezone.utc)
        for r in reminders:
            fire_at = datetime.fromisoformat(r['fire_at'])
            if fire_at.tzinfo is None:
                fire_at = fire_at.replace(tzinfo=timezone.utc)
            remaining = fire_at - now
            mins = int(remaining.total_seconds() // 60)
            time_left = f"in {mins}m" if mins > 0 else "due now!"
            embed.add_field(
                name=f"`{r['id']}` — {time_left}",
                value=r['message'][:100],
                inline=False
            )
        embed.set_footer(text="Cancel: !cancelreminder <id>")
        await message.channel.send(embed=embed)

    async def cancel_reminder(self, message):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("**Usage:** `!cancelreminder <id>`")
            return

        rid     = parts[1]
        user_id = str(message.author.id)
        success = self.db.cancel_reminder(rid, user_id)

        if success:
            await message.channel.send(f"✅ Reminder `{rid}` cancelled.")
        else:
            await message.channel.send(f"⚠️ Reminder `{rid}` not found or doesn't belong to you.")

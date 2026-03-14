import discord
from datetime import datetime

try:
    from leetcode_buddy import get_user_stats
except ImportError:
    def get_user_stats(u): return None


class UserCommands:
    def __init__(self, db):
        self.db = db

    async def register_user(self, message):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!register <leetcode_username>`")
            return

        username   = parts[1]
        discord_id = str(message.author.id)

        # Prevent overwriting an existing registration
        existing = self.db.get_user(discord_id)
        if existing:
            await message.channel.send(
                f"You are already registered as `{existing['leetcode_username']}`. "
                "Use `!unregister` first if you want to switch accounts."
            )
            return

        msg = await message.channel.send(f"Verifying `{username}` on LeetCode...")
        stats = get_user_stats(username)

        if not stats:
            await msg.edit(content=(
                f"Could not verify `{username}`. "
                "Check the spelling or try again later."
            ))
            return

        self.db.set_user(discord_id, {
            'leetcode_username': username,
            'discord_name': str(message.author),
            'registered_date': datetime.utcnow().isoformat(),
            'total_solved': stats.get('total_solved', 0),
            'breakdown': stats.get('breakdown', [0, 0, 0]),
            'last_status': stats.get('solved_today', False),
        })

        await msg.edit(content=(
            f"Registered. `{username}` is now linked to your Discord account.\n"
            "Check your stats with `!mystatus`."
        ))

    async def unregister_user(self, message):
        discord_id = str(message.author.id)
        user = self.db.get_user(discord_id)
        if user:
            uname = user.get('leetcode_username', 'Unknown')
            self.db.delete_user(discord_id)
            await message.channel.send(f"Unregistered `{uname}` from Ghost Squad.")
        else:
            await message.channel.send("You are not registered. Use `!register <username>` to get started.")

    async def show_status(self, message):
        discord_id = str(message.author.id)
        data = self.db.get_user(discord_id)
        if not data:
            await message.channel.send("You are not registered. Use `!register <username>` to get started.")
            return

        status_text = "Completed" if data.get('last_status') else "Not completed"
        easy, med, hard = data.get('breakdown', [0, 0, 0])

        embed = discord.Embed(
            title=data['leetcode_username'],
            color=0x00cc88 if data.get('last_status') else 0xff4444
        )
        embed.add_field(name="Today's Challenge", value=status_text, inline=True)
        embed.add_field(name="Total Solved", value=str(data.get('total_solved', 0)), inline=True)
        embed.add_field(
            name="Breakdown",
            value=f"Easy: {easy}  |  Medium: {med}  |  Hard: {hard}",
            inline=False
        )
        reg_date = data.get('registered_date', '')[:10]
        embed.set_footer(text=f"Member since {reg_date}")
        await message.channel.send(embed=embed)

    async def show_leaderboard(self, message):
        users = self.db.get_all_users()
        if not users:
            await message.channel.send("No users registered yet.")
            return

        sorted_users = sorted(
            users.values(),
            key=lambda x: x.get('total_solved', 0),
            reverse=True
        )

        desc = ""
        for i, u in enumerate(sorted_users[:10], 1):
            status = "Done" if u.get('last_status') else "Pending"
            desc += f"**{i}. {u['leetcode_username']}** — {u.get('total_solved', 0)} solved ({status})\n"

        embed = discord.Embed(title="Ghost Squad Leaderboard", description=desc, color=0xFFD700)
        embed.set_footer(text="Sorted by total problems solved | Use !mystatus for your details")
        await message.channel.send(embed=embed)

    async def show_progress(self, message):
        users = self.db.get_all_users()
        if not users:
            await message.channel.send("No users registered.")
            return

        completed = sum(1 for u in users.values() if u.get('last_status'))
        total = len(users)

        embed = discord.Embed(title="Today's Progress", color=0x3498db)
        embed.description = f"**{completed} out of {total}** members have completed today's challenge."
        for u in users.values():
            status = "Done" if u.get('last_status') else "Pending"
            embed.add_field(name=u['leetcode_username'], value=status, inline=True)

        await message.channel.send(embed=embed)

    async def show_stats(self, message):
        users = self.db.get_all_users()
        if not users:
            await message.channel.send("No data available yet.")
            return

        total_users  = len(users)
        total_solved = sum(u.get('total_solved', 0) for u in users.values())
        active_today = sum(1 for u in users.values() if u.get('last_status'))
        total_easy   = sum(u.get('breakdown', [0, 0, 0])[0] for u in users.values())
        total_med    = sum(u.get('breakdown', [0, 0, 0])[1] for u in users.values())
        total_hard   = sum(u.get('breakdown', [0, 0, 0])[2] for u in users.values())

        embed = discord.Embed(title="Ghost Squad — Community Stats", color=0x9b59b6)
        embed.add_field(name="Members",        value=str(total_users),               inline=True)
        embed.add_field(name="Active Today",   value=f"{active_today}/{total_users}", inline=True)
        embed.add_field(name="Total Solved",   value=str(total_solved),              inline=True)
        embed.add_field(
            name="Combined Difficulty",
            value=f"Easy: {total_easy}  |  Medium: {total_med}  |  Hard: {total_hard}",
            inline=False
        )
        await message.channel.send(embed=embed)
import discord
from datetime import datetime, timedelta
from leetcode_buddy import check

class UserCommands:
    def __init__(self, users_db, save_callback):
        self.users_db = users_db
        self.save_callback = save_callback

    async def register_user(self, message):
        """Register a LeetCode username with Discord account"""
        content = message.content.split()
        if len(content) < 2:
            await message.channel.send("**Usage:** `!register <leetcode_username>`")
            return

        leetcode_username = content[1]
        discord_id = str(message.author.id)
        
        # Validate username exists by checking daily status
        try:
            check(leetcode_username)
        except Exception:
            await message.channel.send(f"**Error:** Unable to verify LeetCode user '{leetcode_username}'. Please check the username.")
            return
        
        self.users_db[discord_id] = {
            'leetcode_username': leetcode_username,
            'registered_date': datetime.now().isoformat()
        }
        self.save_callback()
        
        await message.channel.send(f"**Registration Successful**\nUser: {message.author.mention}\nLeetCode: {leetcode_username}")

    async def show_status(self, message):
        """Show daily challenge status for requesting user"""
        discord_id = str(message.author.id)
        if discord_id not in self.users_db:
            await message.channel.send("**Not Registered**\nUse `!register <username>` to link your LeetCode account.")
            return

        user_data = self.users_db[discord_id]
        username = user_data['leetcode_username']
        solved_today = check(username)
        
        embed = discord.Embed(
            title=f"Status Report: {username}",
            color=0x00ff00 if solved_today else 0xff0000
        )
        embed.add_field(name="Daily Challenge", value="Completed" if solved_today else "Pending", inline=True)
        embed.add_field(name="Registered Since", value=user_data.get('registered_date', 'Unknown')[:10], inline=True)
        
        await message.channel.send(embed=embed)

    async def show_leaderboard(self, message):
        """Display leaderboard sorted by total problems solved"""
        if not self.users_db:
            await message.channel.send("**No Data Available**\nNo users registered yet.")
            return

        loading_msg = await message.channel.send("Fetching leaderboard data...")
        
        leaderboard = []
        for user_id, user_data in self.users_db.items():
            username = user_data['leetcode_username']
            solved_today = check(username)
            leaderboard.append((username, 1 if solved_today else 0, user_id))
        
        self.save_callback()
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(title="Daily Challenge Leaderboard", color=0x0099ff)
        
        for i, (name, status, user_id) in enumerate(leaderboard[:10], 1):
            status_text = "Completed" if status else "Pending"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"<@{user_id}> - {status_text}",
                inline=False
            )
        
        if len(leaderboard) > 10:
            embed.set_footer(text=f"Showing top 10 of {len(leaderboard)} users")
            
        await loading_msg.edit(content="", embed=embed)

    async def show_progress(self, message):
        """Show weekly progress for all users"""
        if not self.users_db:
            await message.channel.send("**No Data Available**\nNo users registered yet.")
            return

        embed = discord.Embed(title="Weekly Progress Report", color=0x9932cc)
        
        for user_id, user_data in self.users_db.items():
            username = user_data['leetcode_username']
            solved_today = check(username)
            status_indicator = "Active" if solved_today else "Inactive"
            
            embed.add_field(
                name=username,
                value=f"<@{user_id}>\nStatus: {status_indicator}",
                inline=True
            )
        
        self.save_callback()
        await message.channel.send(embed=embed)

    async def show_stats(self, message):
        """Show comprehensive statistics"""
        if not self.users_db:
            await message.channel.send("**No Data Available**\nNo users registered yet.")
            return

        total_users = len(self.users_db)
        active_today = 0
        
        for user_data in self.users_db.values():
            username = user_data['leetcode_username']
            if check(username):
                active_today += 1

        embed = discord.Embed(title="Community Statistics", color=0xff9500)
        embed.add_field(name="Total Members", value=str(total_users), inline=True)
        embed.add_field(name="Active Today", value=f"{active_today}/{total_users}", inline=True)
        embed.add_field(name="Daily Completion Rate", value=f"{round((active_today/total_users)*100, 1)}%" if total_users > 0 else "0%", inline=True)
        
        await message.channel.send(embed=embed)

    async def unregister_user(self, message):
        """Remove user registration"""
        discord_id = str(message.author.id)
        if discord_id not in self.users_db:
            await message.channel.send("**Not Registered**\nYou are not currently registered.")
            return

        username = self.users_db[discord_id]['leetcode_username']
        del self.users_db[discord_id]
        self.save_callback()
        
        await message.channel.send(f"**Unregistered Successfully**\nRemoved LeetCode account: {username}")

    async def show_help(self, message):
        """Display available commands"""
        embed = discord.Embed(title="Available Commands", color=0x36393f)
        
        commands = [
            ("!register <username>", "Link your LeetCode account"),
            ("!mystatus", "Check your daily challenge status"),
            ("!leaderboard", "View top performers"),
            ("!progress", "Weekly progress report"),
            ("!stats", "Community statistics"),
            ("!unregister", "Remove your registration"),
            ("!help", "Show this help message"),
            ("", ""),
            ("**Help System Commands**", ""),
            ("!ask <question>", "Post a new question"),
            ("!solve <question_id>", "Mark your question as solved"),
            ("!code <language> <code>", "Share formatted code"),
            ("!questions", "View open questions"),
            ("!helpers", "View top helpers"),
            ("!helpme", "Show help system commands")
        ]
        
        for cmd, desc in commands:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        await message.channel.send(embed=embed)

async def welcome_user(member, channel):
    """Welcome new server members"""
    if channel:
        embed = discord.Embed(
            title=f"Welcome {member.display_name}",
            description="Join our LeetCode community by registering your account with `!register <username>`",
            color=0x00ff00
        )
        embed.add_field(name="Getting Started", value="Use `!help` to see all available commands", inline=False)
        await channel.send(embed=embed)
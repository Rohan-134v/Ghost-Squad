import discord
from datetime import datetime
from leetcode_buddy import get_user_stats

class UserCommands:
    def __init__(self, users_db, save_callback):
        self.users_db = users_db
        self.save_callback = save_callback

    async def register_user(self, message):
        """Link a LeetCode account to Discord"""
        content = message.content.split()
        if len(content) < 2:
            await message.channel.send("**Usage:** `!register <leetcode_username>`")
            return

        username = content[1]
        discord_id = str(message.author.id)
        
        # 1. Verify user exists via API
        msg = await message.channel.send(f"🔍 Verifying user `{username}`...")
        stats = get_user_stats(username)
        
        if not stats:
            await msg.edit(content=f"❌ **Error:** Could not find LeetCode user `{username}`. Check the spelling.")
            return
        
        # 2. Save data with full stats
        self.users_db[discord_id] = {
            'leetcode_username': username,
            'registered_date': datetime.now().isoformat(),
            'total_solved': stats['total_solved'],
            'breakdown': stats['breakdown'],
            'last_status': stats['solved_today']
        }
        self.save_callback()
        
        await msg.edit(content=f"✅ **Success!** Registered `{username}`.\nCheck your stats with `!mystatus`.")

    async def unregister_user(self, message):
        """Remove user from database"""
        discord_id = str(message.author.id)
        if discord_id in self.users_db:
            username = self.users_db[discord_id].get('leetcode_username', 'Unknown')
            del self.users_db[discord_id]
            self.save_callback()
            await message.channel.send(f"🗑️ Unregistered account `{username}`.")
        else:
            await message.channel.send("⚠️ You are not currently registered.")

    async def show_status(self, message):
        """Show the caller's personal status"""
        discord_id = str(message.author.id)
        if discord_id not in self.users_db:
            await message.channel.send("⚠️ You are not registered. Use `!register <username>`.")
            return

        data = self.users_db[discord_id]
        status_emoji = "✅ Completed" if data.get('last_status') else "❌ Pending"
        
        embed = discord.Embed(title=f"👤 {data['leetcode_username']}", color=0x00ff00)
        embed.add_field(name="Daily Challenge", value=status_emoji, inline=True)
        embed.add_field(name="Total Solved", value=str(data.get('total_solved', 0)), inline=True)
        
        # Breakdown visualization
        easy, med, hard = data.get('breakdown', [0,0,0])
        embed.add_field(name="Breakdown", value=f"🟢 {easy} | 🟡 {med} | 🔴 {hard}", inline=False)
        
        await message.channel.send(embed=embed)

    async def show_leaderboard(self, message):
        """Show top 10 users text + Link to Website"""
        if not self.users_db:
            await message.channel.send("⚠️ No users registered yet.")
            return

        # Sort users by total_solved
        sorted_users = sorted(
            self.users_db.values(), 
            key=lambda x: x.get('total_solved', 0), 
            reverse=True
        )

        embed = discord.Embed(title="🏆 LeetCode Leaderboard", color=0xFFD700)
        description = ""
        
        for i, user in enumerate(sorted_users[:10], 1):
            status = "✅" if user.get('last_status') else "⏳"
            description += f"**{i}. {user['leetcode_username']}**\n"
            description += f"   {status} Today | 💎 {user.get('total_solved', 0)} Solved\n\n"
            
        embed.description = description
        embed.set_footer(text="See full analytics on the dashboard!")
        
        # Add website link button/text
        await message.channel.send("🌐 **View Full Dashboard:** http://127.0.0.1:8080 (or your deployed URL)", embed=embed)

    async def show_progress(self, message):
        """Show a quick status report for everyone"""
        if not self.users_db:
            await message.channel.send("⚠️ No users registered.")
            return

        completed = 0
        total = len(self.users_db)
        
        embed = discord.Embed(title="📊 Community Progress", color=0x3498db)
        
        for user_data in self.users_db.values():
            name = user_data['leetcode_username']
            if user_data.get('last_status'):
                completed += 1
                embed.add_field(name=name, value="✅ Done", inline=True)
            else:
                embed.add_field(name=name, value="⏳ Pending", inline=True)
                
        embed.set_footer(text=f"{completed}/{total} users have completed today's challenge.")
        await message.channel.send(embed=embed)

    async def show_stats(self, message):
        """Show community aggregate statistics"""
        if not self.users_db:
            await message.channel.send("⚠️ No data available.")
            return

        total_users = len(self.users_db)
        # Summing total solved for all users
        total_solved_combined = sum(u.get('total_solved', 0) for u in self.users_db.values())
        active_today = sum(1 for u in self.users_db.values() if u.get('last_status'))

        embed = discord.Embed(title="📈 Community Statistics", color=0x9b59b6)
        embed.add_field(name="👥 Members", value=str(total_users), inline=True)
        embed.add_field(name="🔥 Active Today", value=f"{active_today}/{total_users}", inline=True)
        embed.add_field(name="🧠 Combined Problems Solved", value=str(total_solved_combined), inline=False)
        
        await message.channel.send(embed=embed)

    async def show_help(self, ctx):
        """Display all available commands"""
        embed = discord.Embed(title="🤖 LeetCode Bot Commands", color=0x36393f)
        
        # Main Commands
        embed.add_field(name="🎮 **User Commands**", value=(
            "`!register <user>` - Link LeetCode account\n"
            "`!mystatus` - Check your stats\n"
            "`!leaderboard` - View top performers\n"
            "`!progress` - View today's community status\n"
            "`!stats` - View community aggregate stats\n"
            "`!unregister` - Remove your account"
        ), inline=False)

        # AI Commands
        embed.add_field(name="🧠 **AI Tutor**", value=(
            "`!hint <\"problem\"> <\"question\">` - Get a logic hint (No code!)"
        ), inline=False)

        # Help System
        embed.add_field(name="🤝 **Q&A System**", value=(
            "`!ask <question>` - Post a question\n"
            "`!solve <id>` - Mark question solved\n"
            "`!code <lang> <code>` - Share formatted code\n"
            "`!questions` - View open questions\n"
            "`!helpme` - Detailed help system guide"
        ), inline=False)

        await ctx.send(embed=embed)

async def welcome_user(member, channel):
    """Welcome message for new members"""
    embed = discord.Embed(
        title=f"Welcome {member.display_name}!", 
        description="Join our LeetCode community by registering your account!", 
        color=0x00ff00
    )
    embed.add_field(name="Get Started", value="Type `!register <leetcode_username>`", inline=False)
    await channel.send(embed=embed)
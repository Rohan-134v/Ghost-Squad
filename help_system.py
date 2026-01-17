import discord
import json
import random
from datetime import datetime

class HelpSystem:
    def __init__(self, save_callback):
        self.save_callback = save_callback
        self.questions_file = 'questions.json'
        self.reputation_file = 'reputation.json'
        self.questions = self.load_questions()
        self.reputation = self.load_reputation()

    def load_questions(self):
        try:
            with open(self.questions_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_reputation(self):
        try:
            with open(self.reputation_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_questions(self):
        with open(self.questions_file, 'w') as f:
            json.dump(self.questions, f)

    def save_reputation(self):
        with open(self.reputation_file, 'w') as f:
            json.dump(self.reputation, f)

    def generate_question_id(self):
        return f"Q{random.randint(1000, 9999)}"

    async def ask_question(self, message):
        """Post a new help question"""
        content = message.content.split(' ', 1)
        if len(content) < 2:
            await message.channel.send("**Usage:** `!ask <your question title>`")
            return

        question_title = content[1]
        question_id = self.generate_question_id()
        
        # Ensure unique ID
        while question_id in self.questions:
            question_id = self.generate_question_id()

        self.questions[question_id] = {
            'title': question_title,
            'author': str(message.author.id),
            'author_name': message.author.display_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'open',
            'message_id': None
        }

        embed = discord.Embed(
            title=f"Question {question_id}: {question_title}",
            description=f"Asked by {message.author.mention}",
            color=0xff9500,
            timestamp=datetime.now()
        )
        embed.add_field(name="Status", value="Open", inline=True)
        embed.add_field(name="ID", value=question_id, inline=True)
        embed.set_footer(text="Use !solve <ID> when resolved")

        sent_message = await message.channel.send(embed=embed)
        self.questions[question_id]['message_id'] = sent_message.id
        
        # Add reaction for easy interaction
        await sent_message.add_reaction("❓")
        await sent_message.add_reaction("✅")
        
        self.save_questions()

    async def solve_question(self, message):
        """Mark a question as solved"""
        content = message.content.split()
        if len(content) < 2:
            await message.channel.send("**Usage:** `!solve <question_id>`")
            return

        question_id = content[1].upper()
        if question_id not in self.questions:
            await message.channel.send(f"**Error:** Question {question_id} not found.")
            return

        question = self.questions[question_id]
        author_id = str(message.author.id)
        
        # Only author can mark as solved
        if question['author'] != author_id:
            await message.channel.send("**Error:** Only the question author can mark it as solved.")
            return

        question['status'] = 'solved'
        question['solved_by'] = author_id
        question['solved_at'] = datetime.now().isoformat()

        embed = discord.Embed(
            title=f"Question {question_id}: {question['title']}",
            description=f"Asked by <@{question['author']}>",
            color=0x00ff00,
            timestamp=datetime.fromisoformat(question['timestamp'])
        )
        embed.add_field(name="Status", value="Solved", inline=True)
        embed.add_field(name="ID", value=question_id, inline=True)
        embed.set_footer(text="Question marked as solved")

        await message.channel.send(embed=embed)
        self.save_questions()

    async def share_code(self, message):
        """Share formatted code snippet"""
        content = message.content.split(' ', 2)
        if len(content) < 3:
            await message.channel.send("**Usage:** `!code <language> <your code>`\n**Languages:** python, java, cpp, javascript, c")
            return

        language = content[1].lower()
        code = content[2]

        # Language mapping for syntax highlighting
        lang_map = {
            'python': 'py', 'java': 'java', 'cpp': 'cpp', 
            'c++': 'cpp', 'javascript': 'js', 'js': 'js', 'c': 'c'
        }

        if language not in lang_map:
            await message.channel.send("**Supported languages:** python, java, cpp, javascript, c")
            return

        code_id = f"C{random.randint(100, 999)}"
        
        embed = discord.Embed(
            title=f"Code Snippet {code_id}",
            description=f"Shared by {message.author.mention}",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        embed.add_field(name="Language", value=language.title(), inline=True)
        embed.add_field(name="ID", value=code_id, inline=True)
        
        # Format code with syntax highlighting
        formatted_code = f"```{lang_map[language]}\n{code}\n```"
        embed.add_field(name="Code", value=formatted_code, inline=False)
        embed.set_footer(text="React with 👍 if helpful")

        sent_message = await message.channel.send(embed=embed)
        await sent_message.add_reaction("👍")
        await sent_message.add_reaction("🔍")  # For review requests

    async def add_helpful_point(self, user_id):
        """Add reputation point for being helpful"""
        user_id = str(user_id)
        if user_id not in self.reputation:
            self.reputation[user_id] = {'points': 0, 'helped_count': 0}
        
        self.reputation[user_id]['points'] += 1
        self.reputation[user_id]['helped_count'] += 1
        self.save_reputation()

    async def show_helpers(self, message):
        """Show top helpers leaderboard"""
        if not self.reputation:
            await message.channel.send("**No helpers yet!** Start helping others to earn points.")
            return

        # Sort by points
        sorted_helpers = sorted(self.reputation.items(), key=lambda x: x[1]['points'], reverse=True)
        
        embed = discord.Embed(title="Top Helpers", color=0xffd700)
        
        for i, (user_id, data) in enumerate(sorted_helpers[:10], 1):
            points = data['points']
            helped = data['helped_count']
            embed.add_field(
                name=f"{i}. Helper",
                value=f"<@{user_id}>\nPoints: {points} | Helped: {helped}",
                inline=True
            )

        await message.channel.send(embed=embed)

    async def show_questions(self, message):
        """Show recent open questions"""
        open_questions = {k: v for k, v in self.questions.items() if v['status'] == 'open'}
        
        if not open_questions:
            await message.channel.send("**No open questions!** Use `!ask <question>` to post one.")
            return

        embed = discord.Embed(title="Open Questions", color=0xff9500)
        
        # Show last 5 open questions
        recent_questions = list(open_questions.items())[-5:]
        for q_id, q_data in recent_questions:
            embed.add_field(
                name=f"{q_id}: {q_data['title'][:50]}...",
                value=f"By <@{q_data['author']}> | {q_data['timestamp'][:10]}",
                inline=False
            )

        embed.set_footer(text="Use !solve <ID> when you find the answer")
        await message.channel.send(embed=embed)

    async def show_help_commands(self, message):
        """Show help system commands"""
        embed = discord.Embed(title="Help System Commands", color=0x36393f)
        
        commands = [
            ("!ask <question>", "Post a new question"),
            ("!solve <question_id>", "Mark your question as solved"),
            ("!code <language> <code>", "Share formatted code"),
            ("!questions", "View open questions"),
            ("!helpers", "View top helpers"),
            ("!helpme", "Show these commands")
        ]
        
        for cmd, desc in commands:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.set_footer(text="React with 👍 on helpful answers to give reputation points")
        await message.channel.send(embed=embed)
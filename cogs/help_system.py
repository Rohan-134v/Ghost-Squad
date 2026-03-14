"""
cogs/help_system.py — Community Q&A system
"""

import discord
from collections import Counter


class HelpSystem:
    def __init__(self, db):
        self.db = db

    async def ask_question(self, message):
        parts = message.content.split(' ', 1)
        if len(parts) < 2 or not parts[1].strip():
            await message.channel.send("Usage: `!ask <your question here>`")
            return

        question   = parts[1].strip()
        asker_id   = str(message.author.id)
        asker_name = str(message.author.display_name)

        qid = self.db.add_question(asker_id, asker_name, question)

        embed = discord.Embed(
            title="New Question",
            description=question,
            color=0xe67e22
        )
        embed.add_field(name="Asked by",    value=asker_name, inline=True)
        embed.add_field(name="Question ID", value=f"`{qid}`",  inline=True)
        embed.set_footer(text="Reply in the channel to help. Use !solve <id> to mark it solved.")
        await message.channel.send(embed=embed)

    async def solve_question(self, message):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `!solve <question_id>`")
            return

        qid         = parts[1].strip()
        solver_id   = str(message.author.id)
        solver_name = str(message.author.display_name)

        success = self.db.solve_question(qid, solver_id, solver_name)
        if success:
            await message.channel.send(
                f"Question `{qid}` marked as solved by **{solver_name}**. Thanks for helping."
            )
        else:
            await message.channel.send(
                f"Question `{qid}` not found. Use `!questions` to see what's open."
            )

    async def share_code(self, message):
        parts = message.content.split(None, 2)
        if len(parts) < 3:
            await message.channel.send(
                "Usage: `!code <language> <your code>`\n"
                "Example: `!code python def solve(): pass`"
            )
            return

        lang = parts[1].lower()
        code = parts[2]
        await message.channel.send(
            f"Code shared by **{message.author.display_name}**:\n"
            f"```{lang}\n{code}\n```"
        )

    async def show_questions(self, message):
        questions = self.db.get_all_questions()
        open_qs = {k: v for k, v in questions.items() if v.get('status') == 'open'}

        if not open_qs:
            await message.channel.send(
                "No open questions right now. Post one with `!ask <question>`."
            )
            return

        embed = discord.Embed(title="Open Questions", color=0xe67e22)
        for qid, q in list(open_qs.items())[:10]:
            preview = q['question'][:100] + ('...' if len(q['question']) > 100 else '')
            embed.add_field(
                name=f"`{qid}` — {q['asker_name']}",
                value=preview,
                inline=False
            )
        embed.set_footer(text="Reply in the channel to help. Mark done with !solve <id>.")
        await message.channel.send(embed=embed)

    async def show_helpers(self, message):
        questions = self.db.get_all_questions()
        solved = [
            q for q in questions.values()
            if q.get('status') == 'solved' and q.get('solver_name')
        ]
        if not solved:
            await message.channel.send("No solved questions yet. Be the first to help.")
            return

        counts = Counter(q['solver_name'] for q in solved)
        embed = discord.Embed(title="Top Helpers", color=0x2ecc71)
        for i, (name, count) in enumerate(counts.most_common(10), 1):
            embed.add_field(name=f"{i}. {name}", value=f"{count} solved", inline=True)
        await message.channel.send(embed=embed)

    async def show_help_commands(self, message):
        embed = discord.Embed(title="Q&A System Guide", color=0xe67e22)
        embed.add_field(name="Post a question", value="`!ask <question>`",        inline=False)
        embed.add_field(name="Mark as solved",  value="`!solve <id>`",            inline=False)
        embed.add_field(name="Share code",      value="`!code <lang> <code>`",    inline=False)
        embed.add_field(name="View open Qs",    value="`!questions`",             inline=False)
        embed.add_field(name="Top helpers",     value="`!helpers`",               inline=False)
        await message.channel.send(embed=embed)

"""
cogs/placement_feed.py — Placement and internship content commands
"""

import discord
from ai_helper import get_placement_post, get_mock_question


ROADMAP = """
**Ghost Squad — Placement Prep Roadmap**

**Phase 1 — Foundation (Months 1-2)**
- DSA: Arrays, Strings, Linked Lists, Stack, Queue
- CS Fundamentals: Operating Systems, DBMS, Networking basics
- Resume: Draft your one-page resume

**Phase 2 — DSA Intermediate (Months 3-4)**
- Trees, Graphs, Dynamic Programming, Backtracking
- LeetCode: 2 problems per day, Easy to Medium
- Projects: One solid full-stack or ML project

**Phase 3 — Advanced Prep (Month 5)**
- Hard LeetCode problems, System Design basics
- Mock interviews with peers or via Pramp
- Apply to internship portals, LinkedIn, and company sites directly

**Phase 4 — Applications (Month 6 onward)**
- Referrals: reach out to seniors on LinkedIn
- Off-campus: Unstop, Internshala, AngelList
- Track every application in a spreadsheet

**Resources:**
- NeetCode roadmap (neetcode.io)
- Striver's SDE Sheet
- InterviewBit, GeeksforGeeks
- CS50, Abdul Bari on YouTube
"""


class PlacementFeed:
    def __init__(self, db):
        self.db = db

    async def post_tip(self, channel):
        msg = await channel.send("Generating a placement tip...")
        tip = await get_placement_post()
        embed = discord.Embed(
            title="Placement and Internship Tip",
            description=tip,
            color=0xf39c12
        )
        embed.set_footer(text="Ghost Squad | !roadmap for the full prep plan | !mock for interview questions")
        await msg.edit(content=None, embed=embed)
        self.db.log_placement_post(tip)

    async def post_roadmap(self, channel):
        embed = discord.Embed(
            description=ROADMAP,
            color=0x3498db
        )
        embed.set_footer(text="Ghost Squad | Consistency matters more than intensity.")
        await channel.send(embed=embed)

    async def mock_interview(self, message):
        parts = message.content.split(None, 1)
        role = parts[1].strip() if len(parts) > 1 else "Software Development Engineer"

        msg = await message.channel.send(f"Generating a mock question for **{role}**...")
        question = await get_mock_question(role)

        embed = discord.Embed(
            title=f"Mock Interview — {role}",
            description=question,
            color=0x8e44ad
        )
        embed.set_footer(text="Take two minutes to think before answering.")
        await msg.edit(content=None, embed=embed)

    async def resume_tip(self, channel):
        tip = await get_placement_post(
            "Resume writing tips for CS students applying to tech companies"
        )
        embed = discord.Embed(
            title="Resume Tip",
            description=tip,
            color=0x27ae60
        )
        embed.set_footer(text="Ghost Squad | Tailor your resume for each application.")
        await channel.send(embed=embed)

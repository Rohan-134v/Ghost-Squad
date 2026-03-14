"""
ai_helper.py — AI response and placement content generation via Google Gemini
"""

import os
import asyncio
import random
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        except Exception as e:
            print(f"Gemini init failed: {e}")
    return _client


MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """\
You are Ghost Squad AI, a helpful assistant for a college placement and DSA prep community on Discord.

Rules:
1. For DSA or LeetCode problems: give hints and explain the logic only. Do not provide full solution code.
2. For general coding questions (syntax, language features): full code examples are fine.
3. For placement or internship questions: give concrete, actionable advice.
4. Keep responses concise and well-formatted for Discord. Use bullet points where helpful.
5. Be direct and encouraging without being over the top.
"""

PLACEMENT_TOPICS = [
    "Resume tips for CS students applying to product companies",
    "How to ace the HR round and behavioural interviews",
    "Top DSA topics asked in FAANG and product-based companies",
    "How to find and apply for internships as a 2nd or 3rd year student",
    "System design basics every fresher should know",
    "How to write a cold email to a recruiter that actually gets replies",
    "LinkedIn profile optimisation for campus placements",
    "Common mistakes students make during placement season",
    "How to crack online assessments at top companies",
    "Core CS subjects to revise before placements: OS, DBMS, CN",
    "How to negotiate your first offer letter",
    "Internship versus PPO — what you need to know",
    "Top free resources for placement preparation",
    "How to build projects that impress interviewers",
    "Time management during placement season while attending classes",
    "Aptitude and reasoning tips for off-campus drives",
    "How to handle multiple offer deadlines strategically",
    "Mock interview strategies that actually help",
    "GitHub profile tips for freshers",
    "How to prepare for startup interviews versus service companies",
]

PLACEMENT_SYSTEM = """\
You are a senior placement mentor for engineering students in India.
Write a helpful, actionable daily tip for students preparing for campus placements and internships.

Format:
- Start with a bold title using **markdown bold**
- 3 to 5 bullet points of concrete, specific advice
- End with one short motivational sentence
- Keep it under 300 words
- Use Discord markdown: **, bullet points
- Be practical and direct
"""


async def get_ai_response(user_query: str) -> str:
    client = _get_client()
    if not client:
        return "AI is temporarily offline. Check that GOOGLE_API_KEY is set in your .env file."

    if not user_query.strip():
        return "Go ahead and ask your question."

    try:
        from google.genai import types
        loop = asyncio.get_event_loop()

        def _call():
            return client.models.generate_content(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=800,
                ),
                contents=user_query
            )

        response = await loop.run_in_executor(None, _call)
        return response.text.strip() if response.text else "Could not generate a response. Try rephrasing your question."

    except Exception as e:
        print(f"AI Error: {e}")
        return "Something went wrong on my end. Try again in a moment."


async def get_placement_post(topic: str = None) -> str:
    client = _get_client()
    if not client:
        return "AI placement tips are offline. Check that GOOGLE_API_KEY is set."

    if not topic:
        topic = random.choice(PLACEMENT_TOPICS)

    prompt = f"Write a placement tip post about: {topic}"

    try:
        from google.genai import types
        loop = asyncio.get_event_loop()

        def _call():
            return client.models.generate_content(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=PLACEMENT_SYSTEM,
                    max_output_tokens=400,
                ),
                contents=prompt
            )

        response = await loop.run_in_executor(None, _call)
        return response.text.strip() if response.text else f"**{topic}**\n\nKeep grinding."

    except Exception as e:
        print(f"Placement AI Error: {e}")
        return f"**{topic}**\n\nKeep grinding, Ghost Squad."


async def get_mock_question(role: str = "SDE") -> str:
    client = _get_client()
    if not client:
        return "AI is offline."

    prompt = (
        f"Give one challenging interview question for a {role} role at a product company. "
        "Include: the question itself, what skill or concept it tests, "
        "and 2 to 3 hints on how to approach answering it. "
        "Format the response clearly using Discord markdown."
    )

    try:
        from google.genai import types
        loop = asyncio.get_event_loop()

        def _call():
            return client.models.generate_content(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(max_output_tokens=500),
                contents=prompt
            )

        response = await loop.run_in_executor(None, _call)
        return response.text.strip() if response.text else "Could not generate a question right now."

    except Exception as e:
        print(f"Mock AI Error: {e}")
        return "Could not generate a mock question right now. Try again shortly."

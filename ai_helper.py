from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")
# Using the specific model version you confirmed works
MODEL_NAME = "gemini-3-flash-preview"

# Initialize Client
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"❌ Error initializing AI Client: {e}")
    client = None

# Strict Tutor Instructions
SYSTEM_PROMPT = """
You are a LeetCode algorithmic tutor. The user will send a raw query containing a LeetCode problem name and a question.
Your Task:
1. Identify the LeetCode problem name from the user's text.
2. Answer the user's specific question about that problem.
3. NEVER provide full code solutions. Use pseudocode if needed.
4. If the problem name is unclear, ask the user to specify it.
5. Format your response nicely with Markdown.
"""

async def get_hint(user_query):
    if not client:
        return "⚠️ **AI Error:** API Key missing or Client failed to initialize."

    try:
        # Construct the full prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Query: '{user_query}'\n\nProvide a hint:"

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7
            )
        )
        return response.text
            
    except Exception as e:
        error_msg = str(e)
        return f"⚠️ **AI Error:** Connection to model '{MODEL_NAME}' failed. ({error_msg})"
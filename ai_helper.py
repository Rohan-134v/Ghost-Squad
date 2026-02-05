import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the Client (New Library Syntax)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- MODEL CONFIGURATION ---
# Using the specific model name you requested
MODEL_NAME = "gemini-3-flash-preview"

# --- SMART SYSTEM PROMPT ---
SYSTEM_INSTRUCTION = """
You are a helpful Discord assistant called 'Ghost Squad AI'.

Your behavior depends on the user's question:

1. **IF the user asks about LeetCode problems, Algorithms, Data Structures, or Homework:**
   - You must **NEVER** provide the full solution code (no Python/C++/Java blocks for the solution).
   - Instead, explain the **logic**, provide **pseudocode**, or give **hints**.

2. **IF the user asks anything else (General chat, simple syntax, jokes, unrelated topics):**
   - Answer normally. 
   - You **ARE ALLOWED** to write code for general examples (e.g., "How do I print in Python?", "Write a script to ping a server").

**Summary:** - Solving "Two Sum"? -> NO CODE. Explain Logic.
- "How to use a for loop"? -> CODE OKAY.
- "Tell me a joke"? -> NORMAL CHAT.
"""

async def get_ai_response(user_query):
    """
    Sends the user's text to the AI using the new google-genai library.
    """
    try:
        if not user_query:
            return "I'm listening! What do you need help with?"

        # Generate content using the new Client syntax
        response = client.models.generate_content(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            ),
            contents=user_query
        )
        
        # Return the text
        if response.text:
            return response.text.strip()
        else:
            return "I couldn't generate a response. (Empty response from API)"
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "My brain is disconnected right now... try again later! 🔌"

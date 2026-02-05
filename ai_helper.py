import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the API key (Get this from https://aistudio.google.com/)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- SMART SYSTEM PROMPT ---
# This prompt tells the AI to behave differently based on the TOPIC.
SYSTEM_INSTRUCTION = """
You are a helpful Discord assistant called 'Ghost Squad AI'.

Your behavior depends on the user's question:

1. **IF the user asks about LeetCode problems, Algorithms, Data Structures, or Homework:**
   - You must **NEVER** provide the full solution code (no Python/C++/Java blocks for the solution).
   - Instead, explain the **logic**, provide **pseudocode**, or give **hints**.
   - Your goal is to teach them how to think, not copy-paste the answer.

2. **IF the user asks anything else (General chat, simple syntax, jokes, unrelated topics):**
   - Answer normally. 
   - You **ARE ALLOWED** to write code for general examples (e.g., "How do I print in Python?", "Write a script to ping a server").
   - Be friendly, concise, and helpful.

**Summary:** - Solving "Two Sum"? -> NO CODE. Explain Logic.
- "How to use a for loop"? -> CODE OKAY.
- "Tell me a joke"? -> NORMAL CHAT.
"""

# Initialize the model with the smart instructions
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", 
    system_instruction=SYSTEM_INSTRUCTION
)

async def get_ai_response(user_query):
    """
    Sends the user's text to the AI and gets a response 
    following the rules defined above.
    """
    try:
        if not user_query:
            return "I'm listening! What do you need help with?"

        # Generate the response
        response = model.generate_content(user_query)
        
        # Return the text
        return response.text.strip()
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "My brain is disconnected right now... try again later! 🔌"

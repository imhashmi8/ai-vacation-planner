# Import necessary libraries
import json
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
openai=OpenAI()


# Define the system prompt for the AI travel advisor
SYSTEM_PROMPT = """You are a warm and enthusiastic AI travel advisor helping users find their perfect destination.

Ask the user these 5 questions ONE AT A TIME. Wait for their answer before asking the next:
1. What is your current travel mood? (adventurous / relaxed / romantic / cultural)
2. What type of landscape do you prefer? (sea & beach / mountains / waterfalls & forest / desert / vibrant city)
3. Which month are you planning to travel?
4. Who are you travelling with? (solo / couple / family / group of friends)
5. What is your budget range? (budget-friendly / mid-range / luxury)

Once you have all 5 answers, call the recommend_destination tool with your recommendation. Additionally, feel free to ask any follow-up questions to better understand the user's preferences and provide a more personalized recommendation. Always be warm, enthusiastic, and engaging in your responses.

Be conversational, warm, and exciting. Start by greeting the user and asking question 1."""

# Define the tool for recommending a travel destination
tools = [
    {
        "type": "function",
        "function": {
            "name": "recommend_destination",
            "description": "Recommend a travel destination based on the user's preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The recommended travel destination."
                    },
                    "reason": {
                        "type": "string",
                        "description": "A brief explanation of why this destination is recommended based on the user's preferences."
                    },
                    "top_3_things": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "A list of the top 3 things to do or see in the recommended destination."
                    }
                },
                "required": ["destination", "reason", "top_3_things"]
             }
        }
    }
]


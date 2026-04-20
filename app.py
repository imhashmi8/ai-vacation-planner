# Import necessary libraries
import base64
from io import BytesIO
import json
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
from gradio import Image

# Load environment variables from .env file
load_dotenv()

MODEL = "gpt-4o-mini"
VOICE_MODEL = "gpt-4o-mini-tts"
IMAGE_MODEL = "dall-e-3"

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

# Generate a image response
def artist(destination):
    print(f"Generating cinematic image for {destination}...")
    image_response = openai.images.generate(
        model=IMAGE_MODEL,
        prompt=(
            f"A breathtaking cinematic travel photograph of {destination}. "
            "Golden hour lighting, vibrant colors, photorealistic, "
            "professional travel photography, wide angle shot."
        ),
        size="1024x1024",
        quality="standard",
        n=1,
        response_format="b64_json"
    )
    # Prompt → OpenAI API → Base64 Image → Decode → PIL Image → Return
    image_base64 = image_response.data[0].b64_json
    image_data = base64.b64decode(image_base64)
    return Image.open(BytesIO(image_data))

# Generate a voice response

# option 1
# def talker(message):
#     print(f"Generating voice response for message: {message}")
#     audio_response = openai.audio.speech.create(
#         model=VOICE_MODEL,
#         input=message,
#         voice="alloy",  # You can choose different voices if available
#     )
#     return audio_response.content  # This will be the audio data in bytes

# option 2
def talker(args):
    print(f"Generating voice response for message: {args['destination']}")
    text = (
        f"Great choice! {args['destination']} is an amazing destination." 
        f"{args['reason']}"
        f"Top things to do: {', '.join(args['top_3_things'])}."
    )
    response = openai.audio.speech.create(
        model=VOICE_MODEL,
        input=text,
        voice="nova",  # You can choose different voices if available
    )
    audio_path = "travel_recommendation.mp3"
    with open(audio_path, "wb") as audio_file:
        audio_file.write(response.content)
    return audio_path # This will be the audio data in bytes


# Sends the full conversation history + new message to GPT-4o-mini
# Returns either a plain text reply (still asking questions)

# Import necessary libraries
import base64
from io import BytesIO
import json
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

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


# Function to handle the tool call from the AI model
def handle_tool_call(message):
    responses = []
    rec_args = None
    for tool_call in message.tool_calls:
        if tool_call.function.name == "recommend_destination":
            rec_args = json.loads(tool_call.function.arguments)
            things = "\n".join(f"- {t}" for t in rec_args.get("top_3_things", []))
            tool_result = (
                f"Destination: {rec_args['destination']}\n"
                f"Reason: {rec_args['reason']}\n"
                f"Top 3 Things to Do:\n{things}"
            )
            # Append the tool result to the response with the tool call ID for reference
            responses.append({
                "role": "tool",
                "content": tool_result,
                "tool_call_id": tool_call.id
            }  
            )
    return rec_args, responses


def chat(history):
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        max_tokens=500,
    )
    rec_args = None

    while response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        rec_args, tool_responses = handle_tool_call(message)
        messages.append(message)
        messages.extend(tool_responses)
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            max_tokens=500
        )

    reply = response.choices[0].message.content

    # If no tool was called but user has answered all 5 questions (past Q&A phase),
    # force a second call to extract destination from the text reply
    user_turn_count = sum(1 for m in history if m["role"] == "user")
    if rec_args is None and user_turn_count >= 5:
        forced_messages = messages + [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "Please call the recommend_destination tool with the destination you just recommended."}
        ]
        forced_response = openai.chat.completions.create(
            model=MODEL,
            messages=forced_messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "recommend_destination"}}
        )
        if forced_response.choices[0].finish_reason == "tool_calls":
            rec_args, _ = handle_tool_call(forced_response.choices[0].message)

    history = history + [{"role": "assistant", "content": reply}]

    # Trigger image and audio if a destination was extracted
    if rec_args:
        image = artist(rec_args["destination"])
        audio = talker(rec_args)
        image_update = gr.update(value=image, label=f"Recommended Destination: {rec_args['destination']}")
        return history, image_update, audio

    # No recommendation — keep existing image visible
    return history, gr.update(), None


def put_message(history, message):
    return "", history + [{"role": "user", "content": message}]


# Auto-starts with AI greeting on page load
# Sends a hidden trigger message and shows only the assistant greeting
def start_conversation():
    trigger = [{"role": "user", "content": "Hi! I want to find my perfect travel destination."}]
    updated_history, _, _ = chat(trigger)
    greeting_only = [m for m in updated_history if m["role"] == "assistant"]
    return greeting_only, None, None


# Gradio UI - chat on left, image and audio on right
with gr.Blocks(title="AI Travel Recommender") as app:
    gr.Markdown("# 🌍 AI Travel Recommender\nFind your perfect travel destination with the help of our AI travel advisor! Answer a few questions and get personalized recommendations, along with stunning images and voice descriptions of your ideal getaway.")
    
    with gr.Row():
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(label= "AI Travel Advisor", height=480)
            with gr.Row():
                message_input = gr.Textbox(
                    label="Your Message", 
                    placeholder="Type your message here...", 
                    scale=4, 
                    container=False
                    )
                send_button = gr.Button("Send", scale=1)
            clear_button = gr.Button("🔄 Start Over")
        
        with gr.Column(scale=1):
            image_output = gr.Image(label="Recommended Destination", height=380, width=700, interactive=False)
            audio_output = gr.Audio(label="🎙️ Listen to Your Recommendation", type="filepath",autoplay=True)

    send_button.click(fn=put_message, inputs=[chatbot, message_input], outputs=[message_input, chatbot]).then(
        fn=chat, inputs=chatbot, outputs=[chatbot, image_output, audio_output]
    )

    message_input.submit(fn=put_message, inputs=[chatbot, message_input], outputs=[message_input, chatbot]).then(
        fn=chat, inputs=chatbot, outputs=[chatbot, image_output, audio_output]
    )

    clear_button.click(start_conversation, None, [chatbot, image_output, audio_output])

    # Tigger AI greeting on page load
    app.load(start_conversation, None, [chatbot, image_output, audio_output])

if __name__ == "__main__":
    app.launch(theme=gr.themes.Soft(), share=True)
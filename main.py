import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Load API key from Render environment variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Store conversations (temporary memory)
chat_sessions = {}

# 🔥 SYSTEM RULES (THIS FIXES YOUR BOT BEHAVIOR)
SYSTEM_PROMPT = """
You are a helpful AI assistant.
- Give clear and simple answers.
- Do NOT introduce yourself repeatedly.
- Do NOT use formats like short/medium/interesting.
- Continue conversation based on previous messages.
- If user sends an image, describe it normally.
"""

@app.route("/")
def home():
    return "MessageGPT backend running!"

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json.get("user_id", "default")
    message = request.json.get("message", "")
    image_file = request.files.get("image")

    # Create chat history if new user
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]}
        ])

    chat = chat_sessions[user_id]

    try:
        # If image is sent
        if image_file:
            image = Image.open(io.BytesIO(image_file.read()))
            response = chat.send_message([message, image])
        else:
            response = chat.send_message(message)

        return jsonify({"reply": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()

import os
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Conversation memory per user
chat_sessions = {}

# System instructions
SYSTEM_PROMPT = """You are a helpful AI assistant named MessageGPT. Your creator is Aditya.
- Give clear and simple answers.
- Avoid repeating your introduction.
- Continue conversation based on previous messages.
- If an image is sent, describe it normally.
"""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json.get("user_id", "default")
    message = request.json.get("message", "")
    image_file = request.files.get("image")

    # Initialize memory for new user
    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    # Build inputs for Gemini
    inputs = []

    # System prompt only once
    if not chat_sessions[user_id]:
        inputs.append({"text": SYSTEM_PROMPT})

    # Previous conversation
    for entry in chat_sessions[user_id]:
        inputs.append({"text": entry})

    # Current user message
    if message:
        inputs.append({"text": message})

    # Current image (base64)
    if image_file:
        img_bytes = image_file.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        inputs.append({
            "image": {
                "mime_type": image_file.mimetype,
                "data": img_b64
            }
        })

    try:
        # Create a client
        client = genai.Client()

        # Generate AI response
        response = client.generate(
            model="models/gemini-2.5-flash-image",
            input=inputs
        )

        ai_reply = response.output_text

        # Save conversation
        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()

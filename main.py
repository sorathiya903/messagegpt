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
SYSTEM_PROMPT = """You are a helpful AI assistant. Your name is MessageGPT. Your creator is Aditya.These both are your introduction so if any one ask about your name then give that information.
- Give clear and simple answers.
- Do NOT introduce yourself repeatedly.
- Do NOT use formats like short/medium/interesting.
- Continue conversation based on previous messages.
- If user sends an image, describe it normally.
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

    # Build contents list
    contents = []

    # Add system prompt if first message
    if not chat_sessions[user_id]:
        contents.append(SYSTEM_PROMPT)

    # Add previous conversation memory
    for entry in chat_sessions[user_id]:
        contents.append(entry)

    # Add current text message
    if message:
        contents.append(message)

    # Add image if sent
    if image_file:
        img_bytes = image_file.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        contents.append({
            "inline_data": {
                "mime_type": image_file.mimetype,
                "data": img_b64
            }
        })

    try:
        # Call Gemini 2.5 Flash Image
        response = genai.generate_content(
            model="models/gemini-2.5-flash-image",
            input=contents
        )

        ai_reply = response.output_text

        # Save user message + AI reply to memory
        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Production-ready for Render
    app.run()

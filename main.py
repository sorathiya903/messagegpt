import os
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai  # use this import

app = Flask(__name__)
CORS(app)

# Configure your Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Store conversations per user
chat_sessions = {}

SYSTEM_PROMPT = """
You are a helpful AI assistant. Your name is MessageGPT. Your creator is Aditya.These both are your introduction so if any one ask about your name then give that information.
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

    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    # Build messages for the model
    messages = []

    # System prompt only once
    if not chat_sessions[user_id]:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # Previous conversation
    for entry in chat_sessions[user_id]:
        messages.append({"role": "user", "content": entry})

    # Current user message
    if message:
        messages.append({"role": "user", "content": message})

    # Current image (if any)
    if image_file:
        img_bytes = image_file.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        messages.append({
            "role": "user",
            "content": {
                "inline_data": {
                    "mime_type": image_file.mimetype,
                    "data": img_b64
                }
            }
        })

    try:
        # Generate AI response
        response = genai.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=messages
        )

        ai_reply = response.text

        # Update conversation memory
        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()

import os
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
app = Flask(__name__)
CORS(app)

# Initialize Gemini client (reads API key from environment automatically)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Conversation memory per user
chat_sessions = {}

# System prompt to guide AI
SYSTEM_PROMPT = """
You are a helpful AI assistant. Your name is MessageGPT. Your creator is Aditya.These both are your introduction so if any one ask about your name then give that information.
- Give clear and simple answers.
- Do NOT introduce yourself repeatedly.
- Do NOT use formats like short/medium/interesting.
- Continue conversation based on previous messages.
- If user sends an image, describe it normally.
"""

# Utility function to extract plain text from candidate
def extract_text(candidate):
    content = candidate.content
    if hasattr(content, "parts"):
        return "".join(part.text for part in content.parts if hasattr(part, "text"))
    elif hasattr(content, "text"):
        return content.text
    return str(content)

@app.route("/")
def home():
    return render_template("index.html")  # Ensure you have templates/index.html

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.json.get("user_id", "default")
    message = request.json.get("message", "")
    image_file = request.files.get("image")

    # Initialize memory for new user
    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    # Build contents for Gemini
    contents = []

    # Add system prompt only for first message
    if not chat_sessions[user_id]:
        contents.append(SYSTEM_PROMPT)

    # Add previous conversation memory
    for entry in chat_sessions[user_id]:
        contents.append(entry)

    # Add current user message
    if message:
        contents.append(message)

    # Add image if provided
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
        # Call Gemini 2.5 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )

        # Extract clean text
        ai_reply = extract_text(response.candidates[0])

        # Save memory
        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
   app.run()

import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

chat_sessions = {}

SYSTEM_PROMPT = """
You are a helpful AI assistant. Your name is MessageGPT. Your creator is Aditya.These both are your introduction so if any one ask about your name then give that information.
- Give clear and simple answers.
- Do NOT introduce yourself repeatedly.
- Do NOT use formats like short/medium/interesting.
- Continue conversation based on previous messages.
- If user sends an image, describe it normally.
"""

def extract_text(candidate):
    content = candidate.content
    if hasattr(content, "parts"):
        return "".join(part.text for part in content.parts if hasattr(part, "text"))
    return str(content)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.form.get("user_id", "default")
    message = request.form.get("message", "")
    image_file = request.files.get("image")

    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    parts = []

    # System prompt only first time
    if not chat_sessions[user_id]:
        parts.append(types.Part(text=SYSTEM_PROMPT))

    # Memory
    for old in chat_sessions[user_id]:
        parts.append(types.Part(text=old))

    # User message
    if message:
        parts.append(types.Part(text=message))

    # iMAGE (REAL FIX)
    if image_file:
        parts.append(
            types.Part.from_bytes(
                data=image_file.read(),
                mime_type=image_file.mimetype
            )
        )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts
        )

        ai_reply = extract_text(response.candidates[0])

        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()

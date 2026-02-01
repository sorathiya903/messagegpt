import os
import base64
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

# ---------- GEMINI CLIENT ----------
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- CHAT HISTORY ----------
chat_sessions = {}

SYSTEM_PROMPT = """
You are MessageGPT, an AI assistant created by Aditya.If someone asks if you are MessageGPT, then agree that I am MessageGPT. If someone asks for your link or url then give messagegpt.run.place as answer.
Answer clearly, concisely, and stay on topic. 
- Always answer questions about yourself first correctly.
- When asked about general knowledge, answer accurately and only about the topic asked.
- Do not mix previous answers into new unrelated questions.
- Use full sentences and be polite.
- If a question is unclear, ask for clarification instead of guessing.
- Do not provide personal opinions unless explicitly asked.
"""

# ---------- FUNCTIONS ----------
def extract_text(candidate):
    content = candidate.content
    if hasattr(content, "parts"):
        return "".join(part.text for part in content.parts if hasattr(part, "text"))
    return str(content)

def download_image_bytes(url):
    """Download image from URL and return bytes and MIME type."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    mime_type = resp.headers.get("Content-Type", "image/jpeg")
    return resp.content, mime_type

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.form.get("user_id", "default")
    message = request.form.get("message", "")
    image_file = request.files.get("image")  # FileStorage

    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    parts = []

    if not chat_sessions[user_id]:
        parts.append(types.Part(text=SYSTEM_PROMPT))

    for old in chat_sessions[user_id]:
        parts.append(types.Part(text=old))

    if message:
        parts.append(types.Part(text=message))

    if image_file:
        image_bytes = image_file.read()
        parts.append(
            types.Part.from_bytes(data=image_bytes, mime_type=image_file.mimetype)
        )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=parts)]
        )
        ai_reply = extract_text(response.candidates[0])

        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()






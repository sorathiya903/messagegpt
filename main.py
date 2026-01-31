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
You are a helpful AI assistant. Your name is MessageGPT. Your creator is Aditya.
- Give clear and simple answers.
- Do NOT introduce yourself repeatedly.
- Continue conversation based on previous messages.
- If user sends an image, describe it normally.
- If the image contains math and user asks about it, try to solve it.
- If the user sends a image with question then answer that question according to image.
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
    # Get form data
    user_id = request.form.get("user_id", "default")
    message = request.form.get("message", "")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")  # NEW: support image URL

    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    parts = []

    # Add system prompt if first message
    if not chat_sessions[user_id]:
        parts.append(types.Part(text=SYSTEM_PROMPT))

    # Add previous conversation
    for old in chat_sessions[user_id]:
        parts.append(types.Part(text=old))

    # Add current message
    if message:
        parts.append(types.Part(text=message))

    # Handle uploaded image
    if image_file:
        parts.append(types.Part.from_bytes(image_file.read(), mime_type=image_file.mimetype))

    # Handle image URL
    elif image_url:
        try:
            image_bytes, mime_type = download_image_bytes(image_url)
            parts.append(types.Part.from_bytes(image_bytes, mime_type=mime_type))
        except Exception as e:
            return jsonify({"error": f"Failed to fetch image from URL: {str(e)}"}), 400

    try:
        # Call Gemini API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=parts)]
        )

        ai_reply = extract_text(response.candidates[0])

        # Save conversation
        if message:
            chat_sessions[user_id].append(message)
        chat_sessions[user_id].append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()



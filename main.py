import os
import base64
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
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

#  FUNCTIONS
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

#ROUTES 
@app.route("/")
def home():
    return render_template("index.html")

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.form.get("user_id", "default")
    message = request.form.get("message", "")
    uploaded_files = request.files.getlist("files")

    if user_id not in chat_sessions:
        chat_sessions[user_id] = []

    contents = []

    # Add previous structured history
    for item in chat_sessions[user_id]:
        contents.append(item)

    # Build current user parts
    user_parts = []

    if message:
        user_parts.append(types.Part(text=message))

    # Add images
    for file in uploaded_files:
        if file and file.filename != "" and file.mimetype.startswith("image/"):
            image_bytes = file.read()
            user_parts.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=file.mimetype
                )
            )

    # Add current user message
    contents.append(
        types.Content(
            role="user",
            parts=user_parts
        )
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )
        )

        ai_reply = extract_text(response.candidates[0])

        # Save user message properly
        chat_sessions[user_id].append(
            types.Content(role="user", parts=user_parts)
        )

        # Save AI reply properly
        chat_sessions[user_id].append(
            types.Content(
                role="model",
                parts=[types.Part(text=ai_reply)]
            )
        )

        # Limit memory (keep last 20 messages only)
        if len(chat_sessions[user_id]) > 20:
            chat_sessions[user_id] = chat_sessions[user_id][-20:]

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate-image", methods=["POST"])
def generate_image():
    from PIL import Image
    import requests
    import io

    data = request.json
    prompt = data.get("prompt")

    API_URL = "https://router.huggingface.co/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {
        "Authorization": "Bearer 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"
    }

    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})

    if response.status_code != 200:
        return jsonify({"error": response.text}), 400

    image = Image.open(io.BytesIO(response.content))
    image_path = "static/generated.png"
    image.save(image_path)

    return jsonify({"image_url": "/" + image_path})
# RUN 

if __name__ == "__main__":
    app.run()















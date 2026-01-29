from flask import Flask, render_template, request, jsonify
from google import genai
import os

app = Flask(__name__)

# 🔑 Gemini API Key (set in environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Global conversation memory
conversation_history = [
    """You are MessageGPT. MessageGPT is created by Aditya.
You will give short, medium, and interesting answers. Use emojis so that the user feels happy and proud. Explain simply."""
]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    global conversation_history
    data = request.json
    user_input = data.get("message")      # Text
    image_base64 = data.get("image")      # Optional image in base64

    if not user_input and not image_base64:
        return jsonify({"error": "No input received"})

    try:
        # Add user input to conversation memory
        if user_input:
            conversation_history.append(user_input)

        # Optional: Handle image (you can implement actual image processing if supported)
        if image_base64:
            conversation_history.append("[User sent an image]")

        # Trim memory to last 15 messages to save tokens
        conversation_history = conversation_history[-15:]

        # Prepare input for Gemini (must be list of strings)
        contents = []
        for m in conversation_history:
            if isinstance(m, str):
                contents.append(m)
            # Skip dicts or unsupported types

        # Call Gemini
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=contents
        )

        ai_reply = response.text

        # Add AI reply to memory
        conversation_history.append(ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    # Production-ready: host 0.0.0.0, port from environment
    app.run()

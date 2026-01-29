from flask import Flask, render_template, request, jsonify
from google import genai
import os

app = Flask(__name__)

# 🔑 Gemini API Key (set in environment)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")      # Text from user
    image_base64 = data.get("image")      # Image (base64)

    if not user_input and not image_base64:
        return jsonify({"error": "No input received"})

    try:
        parts = []

        # 📝 Add text if exists
        if user_input:
            parts.append(user_input)

        # 🖼 Add image if exists
        if image_base64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }
            })

        # 🤖 Gemini AI request
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=parts
        )

        return jsonify({"reply": response.text})

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)

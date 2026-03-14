import os
import base64
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
import json
import zipfile
import io
import random
import string
import google.generativeai as genaiMap


app = Flask(__name__)
CORS(app)

# ---------- GEMINI CLIENT ----------
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# For mind map
genaiMap.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
    import time
    import os

    print("\n==============================")
    print("🟡 [START] Image Generation Request Received")

    try:
        data = request.json
        prompt = data.get("prompt")

        if not prompt:
            print("🔴 No prompt provided")
            return jsonify({"error": "No prompt provided"}), 400

        print("📝 Prompt:", prompt)

        API_URL = "https://router.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

        headers = {
        "Authorization": "Bearer hf_your_real_token_here",
        "Content-Type": "application/json"
        }



        print("🌍 Sending request to HuggingFace API...")
        start_time = time.time()
        response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": prompt}
        )

        end_time = time.time()
        print(f"⏱ API Response Time: {round(end_time - start_time, 2)} seconds")
        print("📡 Status Code:", response.status_code)
        print("the response was ", response)
        if response.status_code != 200:
            print("🔴 API Error:", response.text)
            return jsonify({"error": response.text}), 400

        print("🖼 Converting response to image...")

        image = Image.open(io.BytesIO(response.content))

        os.makedirs("static", exist_ok=True)
        image_path = "static/generated.png"

        image.save(image_path)

        print("✅ Image saved at:", image_path)
        print("🟢 [SUCCESS] Image generation completed")
        print("==============================\n")

        return jsonify({"image_url": "/" + image_path})

    except Exception as e:
        print("🔥 Unexpected Error:", str(e))
        print("==============================\n")
        return jsonify({"error": str(e)}), 500

@app.route("/generateWeb", methods=["POST"])
def generate():
    user_prompt = request.json["prompt"]
    if user_prompt == 'cal':
        demo='''<!DOCTYPE html> <html> <head> <title>Demo Website</title> <style> body{ font-family:Arial; text-align:center; background:#111; color:white; padding:40px; } h1{ color:#00ffff; } button{ padding:10px 20px; background:#00ffff; border:none; cursor:pointer; } </style> </head> <body> <h1>MessageGPT Demo Website</h1> <p>This is a demo website generated without AI.</p> <button onclick="alert('Hello from Demo Site!')"> Click Me </button> </body> </html>'''
        return jsonify({"html": demo,
                       "status":"success"})
    try:
        

        if not user_prompt:
            print("🔴 No prompt received")
            return jsonify({"error": "No prompt provided"}), 400

        print("🟢 Prompt Got:", user_prompt)
        print("🟡 Starting Generation of Website...")

        final_prompt = f"""
        Create a complete modern responsive HTML website.
        Only return pure HTML with internal CSS and internal JS.
        Do not include explanations.
        Make a website as per the given prompt:
        {user_prompt}
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt
        )

        html_code = response.text

        print("🟢 Website Generated Successfully")
        print("🟡 Sending Output To Frontend JS...")

        return jsonify({
            "status": "success",
            "html": html_code
        })

    except Exception as e:
        print("🔴 Error:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/checkNetlify", methods=["POST"])
def check_domain():

    data = request.json
    name = data["name"]

    domain = f"{name}.netlify.app"

    try:
        r = requests.get(f"https://{domain}", timeout=5)

        if r.status_code == 200:
            return {"available": False}
        else:
            return {"available": True}

    except:
        return {"available": True}


NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")


@app.route("/publishNetlify", methods=["POST"])
def publish_netlify():

    data = request.json
    domain = data["domain"]
    html = data["html"]

    headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    # 1 Create Site
    create_res = requests.post(
        "https://api.netlify.com/api/v1/sites",
        headers=headers,
        json={"name": domain}
    )

    if create_res.status_code not in [200, 201]:
        return jsonify({
            "status": "error",
            "msg": create_res.text
        })

    site = create_res.json()
    site_id = site["id"]

    # 2 Create ZIP with HTML
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("index.html", html)

    zip_buffer.seek(0)

    deploy_headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/zip"
    }

    # 3 Deploy Site
    deploy_res = requests.post(
        f"https://api.netlify.com/api/v1/sites/{site_id}/builds",
        headers=deploy_headers,
        data=zip_buffer.getvalue()
    )

    if deploy_res.status_code not in [200, 201]:
        return jsonify({
            "status": "error",
            "msg": deploy_res.text
        })

    url = f"https://{domain}.netlify.app"

    return jsonify({
        "status": "success",
        "url": url
    })
    print(deploy_res)


@app.route("/mindmap", methods=["POST"])
def generate_mindmap():
    try:
        data = request.json
        topic = data.get("topic")

        prompt = f"""
        Create a detailed mind map for the topic: {topic}
        
        Return ONLY valid JSON.
        
        Structure:
        {{
        "name": "Topic",
        "children": [
          {{
            "name": "Subtopic",
            "children": [
              {{"name": "Detail"}},
              {{"name": "Detail"}}
            ]
          }}
        ]
        }}
        
        Generate maximum 5 branches and educational concepts.
        If a concept is complex then make maximum 8 branches from that topic.
        Don't make long sentences.
        Make small meaningful sentences.
        """

        model = genaiMap.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        mindmap = json.loads(text)
        return jsonify(mindmap)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
























import os
import base64
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS
from google import genai
from google.genai import types
import json
import zipfile
import io
import random
import string
import google.generativeai as genaiMap
import threading
import uuid
from faster_whisper import WhisperModel
from gtts import gTTS
import replicate
import time

app = Flask(__name__)
CORS(app)

# ---------- GEMINI CLIENT ----------
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# For mind map
genaiMap.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- CHAT HISTORY ----------
chat_sessions = {}
jobs = {}

SYSTEM_PROMPT = """
You are MessageGPT, an AI assistant created by Aditya.If someone asks if you are MessageGPT, then agree that I am MessageGPT. If someone asks for your link or url then give messagegpt.run.place as answer. Your development was started from January 2026 by Aditya.
Aditya is a passionate student and self-taught developer with a strong interest in web development and creative technology. He enjoy building interactive and visually appealing web applications using HTML, CSS, and JavaScript. Along with coding, he also have skills in video editing and UI design, which help him to create engaging user experiences.
Aditya has learned many skills like HTML, CSS, Javascript, Python, Flask in Python, a Javascript framework named React and some TailwindCSS and Bootstrap. 
Aditya also works with Github.
Aditya uses Render or Netlify to host websites.
Aditya also knows how to use APIs in Javascript and Python.

Make your answers visually attractive and engaging.

Formatting Rules:
- Always respond in well-structured Markdown with headings (##), subheadings, bullet points, and bold highlights.
- Use clear headings with emojis (like 🚀, 💡, 📊, 💰)
- Break answers into sections
- Use bullet points or numbered lists where helpful
- Highlight important values using **bold**
- Keep paragraphs short (1–2 lines max)
- Add spacing between sections
- Use emojis only where relevant (not too many)
- Don't introduce yourself unless asked.

Response Style:
- If the answer is informational then structure it nicely
- If it includes numbers then show them clearly
- If it's long then divide into sections
- Always avoid large plain paragraphs

Example Style:

🚗 Car Price Overview

💰 Price Range:
- ₹10 lakh to ₹20 lakh

📌 Key Points:
- Good mileage
- Strong engine

⭐ Conclusion:
Short summary

IMPORTANT:
Do NOT return plain paragraphs unless absolutely necessary.
- Always answer questions about yourself first correctly.
- When asked about general knowledge, answer accurately and only about the topic asked.
- Do not mix previous answers into new unrelated questions.
- If a question is unclear, ask for clarification instead of guessing.
- Do not provide personal opinions unless explicitly asked.
"""

#  FUNCTIONS
#from flask import request, Response, jsonify
#import requests, time

#HF_API_KEY = os.environ.get("IMAGE_TOKEN")
HF_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

reclient = replicate.Client(api_token=os.getenv("IMAGE_TOKEN"))

@app.route("/generate-image", methods=["POST"])
def generate_image():
    data = request.get_json()
    prompt = data.get("prompt", "")

    print("⏳ Generating image...")

    output = reclient.run(
        "google/imagen-4",
        input={
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "safety_filter_level": "block_medium_and_above"
        }
    )

    image_bytes = output.read()

    return Response(image_bytes, content_type="image/png")


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


model = WhisperModel("base", compute_type="int8")

@app.route("/voice-chat", methods=["POST"])
def voice_chat():
    try:
        audio_file = request.files["audio"]

        filename = f"temp_{uuid.uuid4()}.webm"
        audio_file.save(filename)

        # speech → Text
        result = model.transcribe(filename)
        user_text = result["text"]

        #  Gemini reply
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text
        )

        ai_reply = extract_text(response.candidates[0])

        #  Text to Speech (men-like)
        tts = gTTS(text=ai_reply, lang="en", tld="co.in")  
        audio_filename = f"static/reply_{uuid.uuid4()}.mp3"
        tts.save(audio_filename)

        return jsonify({
            "text": user_text,
            "reply": ai_reply,
            "audio_url": "/" + audio_filename
        })

    except Exception as e:
        return jsonify({"error": str(e)})
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



def generate_site(job_id, user_prompt):
    try:

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
        html_code = html_code.replace("```html","").replace("```","")

        jobs[job_id]["status"] = "done"
        jobs[job_id]["html"] = html_code

    except Exception as e:

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.route("/generateWeb", methods=["POST"])
def generate():

    data = request.json
    user_prompt = data.get("prompt")

    if not user_prompt:
        return jsonify({"error": "No prompt provided"}), 400

    if user_prompt == "cal":
        demo='''<!DOCTYPE html> <html> <head> <title>Demo Website</title> <style> body{ font-family:Arial; text-align:center; background:#111; color:white; padding:40px; } h1{ color:#00ffff; } button{ padding:10px 20px; background:#00ffff; border:none; cursor:pointer; } </style> </head> <body> <h1>MessageGPT Demo Website</h1> <p>This is a demo website generated without AI.</p> <button onclick="alert('Hello from Demo Site!')"> Click Me </button> </body> </html>'''
        return jsonify({"html": demo, "status": "success"})

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "processing",
        "html": None
    }

    thread = threading.Thread(
        target=generate_site,
        args=(job_id, user_prompt)
    )

    thread.start()

    return jsonify({
        "job_id": job_id
    })


@app.route("/result/<job_id>")
def get_result(job_id):

    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["status"] == "processing":
        return jsonify({"status": "processing"})

    if job["status"] == "error":
        return jsonify({
            "status": "error",
            "message": job["error"]
        })

    return jsonify({
        "status": "done",
        "html": job["html"]
    })

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
























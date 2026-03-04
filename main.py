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
        demo='''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Modern Calculator</title>
            <style>
                /* Basic Reset & Body Styling */
                *, *::before, *::after {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }

                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    color: #e0e0e0;
                }

                /* Calculator Container */
                .calculator {
                    background-color: #282c34;
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                    max-width: 350px;
                    width: 90%;
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                    border: 1px solid #3c3f47;
                }

                /* Display Screen */
                .calculator-display {
                    width: 100%;
                    min-height: 70px;
                    background-color: #3a3f47;
                    border: none;
                    border-radius: 10px;
                    padding: 15px;
                    font-size: 2.8em;
                    text-align: right;
                    color: #ffffff;
                    outline: none;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    letter-spacing: 1px;
                    transition: background-color 0.3s ease;
                    box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.3);
                }
                .calculator-display::placeholder {
                    color: #b0b0b0;
                }

                /* Buttons Grid */
                .calculator-buttons {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 12px;
                }

                /* Individual Button Styling */
                .button {
                    background-color: #4a4e58;
                    border: none;
                    border-radius: 10px;
                    color: #ffffff;
                    font-size: 1.8em;
                    padding: 20px 0;
                    cursor: pointer;
                    transition: all 0.2s ease-in-out;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                    outline: none;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }

                .button:hover {
                    background-color: #5d626c;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
                }

                .button:active {
                    transform: translateY(0);
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
                    background-color: #3e4148;
                }

                /* Operator Buttons */
                .button.operator {
                    background-color: #ff9f1c;
                    color: #282c34;
                    font-weight: bold;
                }
                .button.operator:hover {
                    background-color: #ffa83a;
                }
                .button.operator:active {
                    background-color: #e68e1a;
                }

                /* Clear Button */
                .button.clear {
                    background-color: #e74c3c;
                    color: #ffffff;
                    font-weight: bold;
                }
                .button.clear:hover {
                    background-color: #e95f50;
                }
                .button.clear:active {
                    background-color: #d64032;
                }

                /* Equals Button */
                .button.equals {
                    background-color: #2ecc71;
                    color: #ffffff;
                    font-weight: bold;
                    grid-column: span 2; /* Make it span two columns */
                }
                .button.equals:hover {
                    background-color: #3cda80;
                }
                .button.equals:active {
                    background-color: #27ae60;
                }

                /* Special Styling for Zero Button */
                .button.zero {
                    grid-column: span 2;
                }
            </style>
        </head>
        <body>

            <div class="calculator">
                <input type="text" class="calculator-display" id="display" placeholder="0" readonly>
                <div class="calculator-buttons">
                    <button class="button clear">C</button>
                    <button class="button operator">÷</button>
                    <button class="button operator">×</button>
                    <button class="button operator">-</button>

                    <button class="button">7</button>
                    <button class="button">8</button>
                    <button class="button">9</button>
                    <button class="button operator">+</button>

                    <button class="button">4</button>
                    <button class="button">5</button>
                    <button class="button">6</button>

                    <button class="button">1</button>
                    <button class="button">2</button>
                    <button class="button">3</button>
                    <button class="button equals">=</button>

                    <button class="button zero">0</button>
                    <button class="button">.</button>
                </div>
            </div>

            <script>
                const display = document.getElementById('display');
                const buttons = document.querySelectorAll('.button');

                let currentInput = '';
                let operator = null;
                let previousValue = '';
                let resetDisplay = false;

                buttons.forEach(button => {
                    button.addEventListener('click', () => {
                        const buttonText = button.textContent;

                        if (button.classList.contains('clear')) {
                            currentInput = '';
                            previousValue = '';
                            operator = null;
                            display.value = '0';
                            resetDisplay = false;
                            return;
                        }

                        if (button.classList.contains('operator')) {
                            if (currentInput === '' && previousValue === '') return; // No input yet

                            if (previousValue !== '' && operator && currentInput !== '') {
                                calculate();
                                currentInput = display.value; // Use the result as the new currentInput
                                previousValue = ''; // Clear previous value after calculation
                            }
                            
                            if (currentInput !== '') {
                                previousValue = currentInput;
                            }
                            operator = buttonText;
                            currentInput = ''; // Clear currentInput for the next number
                            resetDisplay = true;
                            return;
                        }

                        if (button.classList.contains('equals')) {
                            if (previousValue === '' || operator === null) return;
                            calculate();
                            operator = null;
                            previousValue = '';
                            resetDisplay = true; // After equals, next number starts fresh
                            return;
                        }

                        // If it's a number or decimal
                        if (resetDisplay) {
                            currentInput = buttonText;
                            resetDisplay = false;
                        } else {
                            // Prevent multiple decimals
                            if (buttonText === '.' && currentInput.includes('.')) return;
                            // Prevent leading zero if not a decimal
                            if (currentInput === '0' && buttonText !== '.') {
                                currentInput = buttonText;
                            } else {
                                currentInput += buttonText;
                            }
                        }
                        display.value = currentInput;
                    });
                });

                function calculate() {
                    let result;
                    const prev = parseFloat(previousValue);
                    const current = parseFloat(currentInput);

                    if (isNaN(prev) || isNaN(current)) return;

                    switch (operator) {
                        case '+':
                            result = prev + current;
                            break;
                        case '-':
                            result = prev - current;
                            break;
                        case '×':
                            result = prev * current;
                            break;
                        case '÷':
                            result = prev / current;
                            break;
                        default:
                            return;
                    }
                    display.value = (Math.round(result * 100000000) / 100000000).toString(); // Handle floating point precision
                    currentInput = display.value;
                }

                // Initialize display
                display.value = '0';
            </script>
        </body>
        </html>
        '''
        return jsonify({"html": demo})
    try:
        user_prompt = request.json.get("prompt")

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
# RUN 

if __name__ == "__main__":
    app.run()





















"""Multi-model chat backend (Flask + Google Gemini).

The browser never sees the API key: it sends the chosen model and the
chat history here, and this server calls the Gemini API.
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import errors, types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

# Models offered in the dropdown. Override in .env, comma-separated.
# The "-latest" aliases always point at Google's current version.
MODELS = [
    m.strip()
    for m in os.getenv("MODELS", "gemini-flash-latest,gemini-flash-lite-latest").split(",")
    if m.strip()
]

MAX_MESSAGE_CHARS = 8000
REQUEST_TIMEOUT_MS = 60_000

app = Flask(__name__, static_folder="static")

# Create the client once; if the key is missing we still start, and report
# the problem in the chat instead of crashing.
client = (
    genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
    if API_KEY
    else None
)


def to_gemini_contents(messages):
    """Convert [{role: 'user'|'assistant', content: str}] to Gemini's format."""
    contents = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        text = str(m.get("content", "")).strip()
        if text:
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return contents


def error(message, status):
    return jsonify(error=message), status


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/models")
def list_models():
    return jsonify(models=MODELS)


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be JSON.", 400)

    model = data.get("model")
    messages = data.get("messages")

    # --- Validate input -------------------------------------------------
    if model not in MODELS:
        return error(f"Unknown model: {model!r}", 400)
    if not isinstance(messages, list) or not messages:
        return error("No messages provided.", 400)
    if messages[-1].get("role") != "user" or not str(messages[-1].get("content", "")).strip():
        return error("The last message must be a non-empty user message.", 400)
    if len(str(messages[-1]["content"])) > MAX_MESSAGE_CHARS:
        return error(f"Message is too long (max {MAX_MESSAGE_CHARS} characters).", 400)
    if client is None:
        return error("Server is missing GEMINI_API_KEY. Add it to the .env file and restart.", 500)

    # --- Call the model ---------------------------------------------------
    try:
        response = client.models.generate_content(
            model=model,
            contents=to_gemini_contents(messages),
        )
        reply = response.text
        if not reply:
            # Happens e.g. when a response is blocked by safety filters.
            reason = None
            if response.candidates:
                reason = response.candidates[0].finish_reason
            return error(f"The model returned no text (finish reason: {reason}).", 502)
        return jsonify(reply=reply, model=model)

    except errors.ClientError as e:  # 4xx from Google
        if e.code == 429:
            return error("Rate limit or quota exceeded. Wait a moment and try again.", 429)
        if e.code in (401, 403):
            return error("The API key was rejected. Check GEMINI_API_KEY.", 502)
        if e.code == 404:
            return error(f"Model {model!r} was not found. Run list_models.py to see valid names.", 502)
        return error(f"Request rejected by the API ({e.code}): {e.message}", 502)
    except errors.ServerError as e:  # 5xx from Google
        return error(f"The model service had a problem ({e.code}). Try again shortly.", 503)
    except errors.APIError as e:
        return error(f"API error ({e.code}): {e.message}", 502)
    except Exception as e:  # timeouts, network failures, anything unexpected
        app.logger.exception("Unexpected error calling Gemini")
        return error(f"Could not reach the model: {type(e).__name__}", 504)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

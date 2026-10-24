# Multi-Model Chat (Assignment #13)

A web chat app that lets you pick between several Google Gemini models, keeps the conversation history for the session, and reports API errors in the chat instead of crashing.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

Put your key from Google AI Studio into `.env` as `GEMINI_API_KEY`.

Optionally run `python list_models.py` to see which models your key can use, and set `MODELS` in `.env` to any two or more of them.

## Run

```bash
python app.py
```

Open http://localhost:5000.

## How it meets the requirements

| Requirement | Where |
|---|---|
| At least two models | `MODELS` in `app.py` / `.env`, served by `GET /api/models` |
| Model selector | `<select id="model">` in `static/index.html` |
| Chat interface | Text box + Send (Enter sends, Shift+Enter adds a new line) |
| Displays responses | `addBubble()` in `static/script.js`, each reply labelled with its model |
| Session history | `history` array in `script.js`, sent in full with every request so the model keeps context; "Clear chat" resets it |
| Error handling | Backend validates input and catches every API error (bad key, unknown model, 429 rate limit, 5xx, timeouts, blocked replies) and returns a JSON error; the frontend catches network and server errors, shows them in the chat, and restores your message so you can retry |

## Architecture

```
Browser (HTML/CSS/JS)  --POST /api/chat {model, messages}-->  Flask (app.py)  --> Gemini API
                       <-- {reply} or {error} ---------------
```

The API key stays on the server; the browser never sees it.

## Testing the error handling

- Remove `GEMINI_API_KEY` from `.env` → "Server is missing GEMINI_API_KEY".
- Use a wrong key → "The API key was rejected".
- Add a fake model name to `MODELS` and pick it → "Model … was not found".
- Stop the server while the page is open and send a message → "Network error".

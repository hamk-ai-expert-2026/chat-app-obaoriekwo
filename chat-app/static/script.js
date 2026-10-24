// Chat history for this session: [{ role: "user" | "assistant", content, model? }]
let history = [];
let busy = false;

const els = {
  model: document.getElementById("model"),
  messages: document.getElementById("messages"),
  form: document.getElementById("chat-form"),
  input: document.getElementById("input"),
  send: document.getElementById("send"),
  clear: document.getElementById("clear"),
};

// ---------- Rendering ----------

function addBubble(kind, text, meta) {
  const empty = els.messages.querySelector(".empty");
  if (empty) empty.remove();

  const div = document.createElement("div");
  div.className = `msg ${kind}`;
  if (meta) {
    const m = document.createElement("span");
    m.className = "meta";
    m.textContent = meta;
    div.appendChild(m);
  }

  const body = document.createElement("div");
  if (kind === "assistant" && window.marked && window.DOMPurify) {
    body.className = "md";
    // marked turns Markdown into HTML; DOMPurify strips anything unsafe
    body.innerHTML = DOMPurify.sanitize(marked.parse(text));
  } else {
    body.textContent = text; // user messages, errors, or libraries failed to load
  }
  div.appendChild(body);

  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

function setBusy(value) {
  busy = value;
  els.send.disabled = value;
  els.input.disabled = value;
}

// ---------- Models ----------

async function loadModels() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { models } = await res.json();
    els.model.innerHTML = "";
    for (const name of models) {
      const opt = document.createElement("option");
      opt.value = opt.textContent = name;
      els.model.appendChild(opt);
    }
    els.model.disabled = false;
  } catch (err) {
    addBubble("error", `Could not load the model list (${err.message}). Is the server running?`);
  }
}

// ---------- Sending ----------

async function sendMessage(text) {
  const model = els.model.value;
  history.push({ role: "user", content: text });
  addBubble("user", text);
  setBusy(true);
  const thinking = addBubble("assistant thinking", "Thinking…", model);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Send only role + content; the server doesn't need our extra fields.
      body: JSON.stringify({
        model,
        messages: history.map(({ role, content }) => ({ role, content })),
      }),
    });

    let data = {};
    try { data = await res.json(); } catch { /* non-JSON error page */ }

    if (!res.ok) throw new Error(data.error || `Server error (HTTP ${res.status})`);

    thinking.remove();
    history.push({ role: "assistant", content: data.reply, model });
    addBubble("assistant", data.reply, model);
  } catch (err) {
    thinking.remove();
    // Drop the failed user turn from history so the conversation stays valid,
    // and put the text back in the box so the user can retry.
    history.pop();
    els.input.value = text;
    const msg = err instanceof TypeError ? "Network error: could not reach the server." : err.message;
    addBubble("error", msg);
  } finally {
    setBusy(false);
    els.input.focus();
  }
}

// ---------- Events ----------

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = els.input.value.trim();
  if (!text || busy || els.model.disabled) return;
  els.input.value = "";
  sendMessage(text);
});

els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.form.requestSubmit();
  }
});

els.clear.addEventListener("click", () => {
  history = [];
  els.messages.innerHTML = '<p class="empty">Chat cleared. Say hello.</p>';
  els.input.focus();
});

loadModels();
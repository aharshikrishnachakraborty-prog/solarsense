// Chat assistant: a small button in the corner of every page that opens a chat panel.
// Questions go to /api/chat; the server adds facts our code computed and asks Google Gemini to phrase
// the answer (engine/assistant.py). The AI never invents numbers, and its key never reaches the browser.

const CHAT_ICON = `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor"
  d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 6.5a1.5 1.5 0 1 0 0
  .01zm5 0a1.5 1.5 0 1 0 0 .01zm5 0a1.5 1.5 0 1 0 0 .01z"/></svg>`;
const CLOSE_ICON = `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor"
  d="M6.4 5 5 6.4 10.6 12 5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6L19 6.4 17.6 5 12 10.6z"/></svg>`;
const CHAT_SUGGESTIONS = ["Summary of the selected day", "Weekly report", "Whole period report", "Which inverters need attention?"];
const CHAT_HISTORY_KEY = "solarsense-chat";

const Chat = {
  busy: false,

  /** Add the button and the (hidden) panel to the page, and restore this tab's conversation. */
  mount() {
    const box = document.createElement("div");
    box.className = "chat";
    box.innerHTML = `
      <button class="chat-toggle" type="button" aria-label="Open the SolarSense assistant" title="Ask the assistant">${CHAT_ICON}</button>
      <section class="chat-panel" role="dialog" aria-label="SolarSense assistant" hidden>
        <header class="chat-head">
          <div><strong>SolarSense Assistant</strong><div class="chat-sub" id="chat-context"></div></div>
          <button class="chat-close" type="button" aria-label="Close">${CLOSE_ICON}</button>
        </header>
        <div class="chat-log" id="chat-log" aria-live="polite"></div>
        <div class="chat-chips" id="chat-chips">
          ${CHAT_SUGGESTIONS.map((s) => `<button type="button" class="chat-chip">${escapeHTML(s)}</button>`).join("")}
        </div>
        <form class="chat-form" id="chat-form">
          <input id="chat-input" type="text" maxlength="500" autocomplete="off" placeholder="Ask about output, losses or alerts…" aria-label="Your question">
          <button type="submit">Send</button>
        </form>
      </section>`;
    document.body.appendChild(box);

    box.querySelector(".chat-toggle").addEventListener("click", () => Chat.open(true));
    box.querySelector(".chat-close").addEventListener("click", () => Chat.open(false));
    box.querySelectorAll(".chat-chip").forEach((chip) => chip.addEventListener("click", () => Chat.ask(chip.textContent)));
    document.getElementById("chat-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.getElementById("chat-input");
      if (input.value.trim()) Chat.ask(input.value.trim());
      input.value = "";
    });

    const history = Chat.history();
    if (history.length) history.forEach((m) => Chat.show(m.role, m.text, false, m.inverters));
    else Chat.show("bot", "Hi. I can summarise a day, a week or the whole period for the selected plant, "
      + "and explain alerts and losses. Every number comes from the SolarSense results.", false);
    if (session.get("solarsense-chat-open")) Chat.open(true);
  },

  open(show) {
    session.set("solarsense-chat-open", show ? "1" : "");   // stay open after following a link
    document.querySelector(".chat-panel").hidden = !show;
    document.querySelector(".chat-toggle").hidden = show;
    if (show) {
      const s = Layout.state;
      document.getElementById("chat-context").textContent = s.plant ? `Plant ${s.plant} · ${fmt.date(s.date)}` : "";
      document.getElementById("chat-input").focus();
    }
  },

  /** Conversation of this browser tab (cleared when the tab closes). */
  history() {
    try { return JSON.parse(window.sessionStorage.getItem(CHAT_HISTORY_KEY)) || []; } catch (e) { return []; }
  },

  sessionId() {
    let id = session.get("solarsense-chat-id");
    if (!id) { id = Math.random().toString(36).slice(2, 12); session.set("solarsense-chat-id", id); }
    return id;
  },

  /** Put one message bubble in the log (and remember it unless told not to). */
  show(role, text, remember = true, inverters = {}) {
    const log = document.getElementById("chat-log");
    const bubble = document.createElement("div");
    bubble.className = `chat-msg ${role}`;
    bubble.innerHTML = Chat.format(text, inverters);
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    if (remember) {
      const history = [...Chat.history(), { role, text, inverters }].slice(-30);
      session.set(CHAT_HISTORY_KEY, JSON.stringify(history));
    }
    return bubble;
  },

  /** Link to a page for the current plant and date, e.g. "plant.html?plant=2&date=2020-05-27". */
  pageLink(href, extra = {}) {
    const { plant, date } = Layout.state;
    const params = new URLSearchParams({ ...extra, ...(plant ? { plant } : {}), ...(date ? { date } : {}) });
    if (extra.plant) params.set("plant", extra.plant);
    return `${href}?${params}`;
  },

  /** Turn "the Alerts page" and real inverter IDs (sent by the server) into links. Runs on escaped text. */
  addLinks(html, inverters) {
    // Page names have no regex symbols; "&" is already escaped to "&amp;" in the text, so escape the name too.
    const pages = PAGES.filter((p) => p.key !== "about").map((p) => ({ ...p, pattern: escapeHTML(p.label) }));
    for (const p of pages) {
      const words = new RegExp(`\\b(${p.pattern}) page\\b`, "g");
      html = html.replace(words, `<a class="chat-link" href="${Chat.pageLink(p.href)}">$1 page</a>`);
    }
    for (const [inverter, plant] of Object.entries(inverters || {})) {
      const href = Chat.pageLink("inverter.html", { id: inverter, plant });
      html = html.split(inverter).join(`<a class="chat-link" href="${href}">${inverter}</a>`);
    }
    return html;
  },

  /** Very small markdown: **bold**, "# " headings, "- " bullets, plus links (text is escaped first, so it can't become code). */
  format(text, inverters = {}) {
    const safe = escapeHTML(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    const lines = Chat.addLinks(safe, inverters).split("\n");
    let html = "", inList = false;
    for (let line of lines) {
      const bullet = line.match(/^\s*[-*•]\s+(.*)/);
      const heading = line.match(/^\s*#{1,6}\s+(.*)/);   // "### Title" -> bold line
      if (heading) line = `<strong>${heading[1]}</strong>`;
      if (bullet && !inList) { html += "<ul>"; inList = true; }
      if (!bullet && inList) { html += "</ul>"; inList = false; }
      html += bullet ? `<li>${bullet[1]}</li>` : (line.trim() ? `<p>${line}</p>` : "");
    }
    return inList ? `${html}</ul>` : html;
  },

  /** Send a question and show the answer (one question at a time). */
  async ask(question) {
    if (Chat.busy) return;
    Chat.busy = true;
    Chat.show("user", question);
    const typing = Chat.show("bot typing", "Thinking…", false);
    let answer;
    try {
      answer = await Chat.fetchReply(question);
    } catch (error) {
      answer = { reply: "The assistant is offline right now. Every number is still on the dashboard pages." };
    }
    typing.remove();
    Chat.show("bot", answer.reply, true, answer.inverters);
    Chat.busy = false;
  },

  async fetchReply(question) {
    const { plant, date } = Layout.state;
    const sessionId = Chat.sessionId();
    // The static copy has no server to keep the AI key secret, so the assistant only runs on the live server.
    if (STATIC_SITE) return { reply: "The assistant runs on the live SolarSense server. On this demo copy it is switched off." };
    const response = await fetch("api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, plant, date, session_id: sessionId }) });
    if (!response.ok) throw new Error("chat failed");
    return response.json();
  },
};

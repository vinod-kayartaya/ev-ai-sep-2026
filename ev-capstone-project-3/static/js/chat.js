/**
 * OmniSupport AI - Frontend Chat Application
 * Handles sessions, conversation history, RAG grounding sources, and markdown rendering.
 */

// Global State
let currentSession = null;
let productMetadata = {};

document.addEventListener("DOMContentLoaded", () => {
  initMarkdown();
  loadProducts();
  checkExistingSession();
  bindEvents();
});

// Configure Marked.js for markdown rendering
function initMarkdown() {
  if (window.marked) {
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (window.hljs) {
          const language = hljs.getLanguage(lang) ? lang : "plaintext";
          return hljs.highlight(code, { language }).value;
        }
        return code;
      }
    });
  }
}

// Fetch products and sample questions
async function loadProducts() {
  try {
    const res = await fetch("/api/products");
    const data = await res.json();
    productMetadata = data.metadata || {};
  } catch (err) {
    console.error("Failed to load products metadata:", err);
  }
}

// Check if an active session is saved in localStorage
async function checkExistingSession() {
  const savedSessionId = localStorage.getItem("omni_active_session_id");
  if (savedSessionId) {
    try {
      const res = await fetch(`/api/sessions/${savedSessionId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.session) {
          currentSession = data.session;
          switchToChatView(currentSession);
          renderMessageHistory(data.messages || []);
          return;
        }
      }
    } catch (e) {
      console.warn("Could not restore saved session:", e);
      localStorage.removeItem("omni_active_session_id");
    }
  }
  // Otherwise default to Start Session View
  switchToStartView();
}

// Bind all UI event handlers
function bindEvents() {
  // Product select change -> update quick prompts
  const productSelect = document.getElementById("custProduct");
  if (productSelect) {
    productSelect.addEventListener("change", handleProductChange);
  }

  // Start Session Form Submit
  const startForm = document.getElementById("startSessionForm");
  if (startForm) {
    startForm.addEventListener("submit", handleStartSession);
  }

  // Send Message Form Submit
  const sendForm = document.getElementById("sendMessageForm");
  if (sendForm) {
    sendForm.addEventListener("submit", handleSendMessage);
  }

  // Textarea Enter key handling (Enter to send, Shift+Enter for new line)
  const messageInput = document.getElementById("userMessageInput");
  if (messageInput) {
    messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendForm.dispatchEvent(new Event("submit"));
      }
    });
  }

  // New Session button in navbar
  document.getElementById("btnNewSession")?.addEventListener("click", () => {
    if (currentSession && currentSession.status === "active") {
      if (!confirm("Starting a new session will close your view of this conversation. Proceed?")) {
        return;
      }
    }
    startFreshSession();
  });

  // End Session button in chat
  document.getElementById("btnEndSession")?.addEventListener("click", () => {
    const modal = new bootstrap.Modal(document.getElementById("confirmEndModal"));
    modal.show();
  });

  // Confirm End Session button in modal
  document.getElementById("btnConfirmEndAction")?.addEventListener("click", handleEndSession);

  // Restart conversation button in ended session banner
  document.getElementById("btnRestartAfterEnd")?.addEventListener("click", startFreshSession);

  // Export Transcript
  document.getElementById("btnExportTranscript")?.addEventListener("click", exportTranscript);

  // Past Sessions Modal trigger
  document.getElementById("btnOpenHistory")?.addEventListener("click", openHistoryModal);

  // Knowledge Base Explorer trigger
  document.getElementById("btnOpenKB")?.addEventListener("click", openKBModal);

  // KB Product filter change
  document.getElementById("kbProductFilter")?.addEventListener("change", loadKBTickets);
}

// Handle product dropdown change
function handleProductChange(e) {
  const product = e.target.value;
  const meta = productMetadata[product];
  const taglineEl = document.getElementById("productTagline");
  const promptsContainer = document.getElementById("quickPromptsContainer");
  const promptChipsEl = document.getElementById("quickPromptChips");

  if (meta) {
    taglineEl.textContent = meta.tagline || "";
    if (meta.sample_questions && meta.sample_questions.length > 0) {
      promptChipsEl.innerHTML = "";
      meta.sample_questions.forEach(q => {
        const chip = document.createElement("div");
        chip.className = "prompt-chip";
        chip.textContent = q;
        chip.title = "Click to use this sample query";
        chip.addEventListener("click", () => {
          document.getElementById("custQuery").value = q;
          document.getElementById("custQuery").focus();
        });
        promptChipsEl.appendChild(chip);
      });
      promptsContainer.classList.remove("d-none");
    } else {
      promptsContainer.classList.add("d-none");
    }
  } else {
    taglineEl.textContent = "";
    promptsContainer.classList.add("d-none");
  }
}

// Start a new session
async function handleStartSession(e) {
  e.preventDefault();

  const name = document.getElementById("custName").value.trim();
  const email = document.getElementById("custEmail").value.trim();
  const product = document.getElementById("custProduct").value;
  const initialQuery = document.getElementById("custQuery").value.trim();

  if (!name || !email || !product || !initialQuery) {
    alert("Please fill in all required fields.");
    return;
  }

  const btn = document.getElementById("btnSubmitStart");
  const spinner = document.getElementById("startSpinner");
  const icon = document.getElementById("startIcon");

  btn.disabled = true;
  spinner.classList.remove("d-none");
  icon.classList.add("d-none");

  try {
    const res = await fetch("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        email: email,
        product: product,
        initial_query: initialQuery
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to start session.");
    }

    currentSession = data.session;
    localStorage.setItem("omni_active_session_id", currentSession.session_id);

    switchToChatView(currentSession);
    renderMessageHistory(data.messages || []);

  } catch (err) {
    alert("Error starting conversation: " + err.message);
  } finally {
    btn.disabled = false;
    spinner.classList.add("d-none");
    icon.classList.remove("d-none");
  }
}

// Send follow-up message in active session
async function handleSendMessage(e) {
  e.preventDefault();
  if (!currentSession) return;

  const inputEl = document.getElementById("userMessageInput");
  const messageText = inputEl.value.trim();
  if (!messageText) return;

  // Append user message immediately to UI
  const tempUserMsg = {
    sender: "user",
    message: messageText,
    timestamp: new Date().toISOString()
  };
  appendMessage(tempUserMsg);

  inputEl.value = "";
  inputEl.disabled = true;
  document.getElementById("btnSendMessage").disabled = true;
  showTypingIndicator(true);

  try {
    const res = await fetch(`/api/sessions/${currentSession.session_id}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: messageText })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || "Failed to get response.");
    }

    // Append AI response
    appendMessage(data.assistant_message);

  } catch (err) {
    appendMessage({
      sender: "assistant",
      message: `**Error:** ${err.message}`,
      timestamp: new Date().toISOString()
    });
  } finally {
    showTypingIndicator(false);
    if (currentSession.status === "active") {
      inputEl.disabled = false;
      document.getElementById("btnSendMessage").disabled = false;
      inputEl.focus();
    }
  }
}

// End current session
async function handleEndSession() {
  if (!currentSession) return;

  try {
    const res = await fetch(`/api/sessions/${currentSession.session_id}/end`, {
      method: "POST"
    });
    const data = await res.json();
    if (res.ok && data.success) {
      currentSession.status = "ended";
      localStorage.removeItem("omni_active_session_id");
      updateSessionStatusUI("ended");
      
      // Close confirmation modal
      const modalEl = document.getElementById("confirmEndModal");
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      // Append system ending note
      appendMessage({
        sender: "assistant",
        message: "*This conversation has been closed by the customer. Thank you for contacting OmniSupport!*",
        timestamp: new Date().toISOString()
      });
    }
  } catch (err) {
    alert("Failed to end session: " + err.message);
  }
}

// Start fresh session (return to form)
function startFreshSession() {
  const previousName = currentSession ? currentSession.customer_name : "";
  const previousEmail = currentSession ? currentSession.customer_email : "";
  const previousProduct = currentSession ? currentSession.product : "";

  currentSession = null;
  localStorage.removeItem("omni_active_session_id");

  switchToStartView();

  // Restore fields for quick convenience
  if (previousName) document.getElementById("custName").value = previousName;
  if (previousEmail) document.getElementById("custEmail").value = previousEmail;
  if (previousProduct) {
    const select = document.getElementById("custProduct");
    select.value = previousProduct;
    select.dispatchEvent(new Event("change"));
  }
  document.getElementById("custQuery").value = "";
}

// Switch UI to Start Session View
function switchToStartView() {
  document.getElementById("startSessionView").classList.remove("d-none");
  document.getElementById("activeChatView").classList.add("d-none");
  document.getElementById("navSessionInfo").classList.add("d-none");
}

// Switch UI to Active Chat View
function switchToChatView(session) {
  document.getElementById("startSessionView").classList.add("d-none");
  document.getElementById("activeChatView").classList.remove("d-none");
  document.getElementById("navSessionInfo").classList.remove("d-none");

  // Populate nav info
  document.getElementById("navCustomerName").textContent = session.customer_name;
  document.getElementById("navProductBadge").textContent = session.product;

  // Populate chat header
  document.getElementById("chatHeaderCustomerName").textContent = session.customer_name;
  document.getElementById("chatHeaderCustomerEmail").textContent = session.customer_email;
  document.getElementById("chatProductBadge").textContent = session.product;
  document.getElementById("chatSessionIdShort").textContent = session.session_id.substring(0, 8) + "...";
  document.getElementById("chatSessionIdShort").title = session.session_id;

  updateSessionStatusUI(session.status);

  // Clear messages container
  document.getElementById("chatMessages").innerHTML = "";
}

// Update UI elements based on active/ended status
function updateSessionStatusUI(status) {
  const isEnded = status === "ended";

  const chatStatusBadge = document.getElementById("chatStatusBadge");
  const navSessionStatus = document.getElementById("navSessionStatus");
  const endedBanner = document.getElementById("endedSessionBanner");
  const inputArea = document.getElementById("chatInputArea");
  const btnEndSession = document.getElementById("btnEndSession");

  if (isEnded) {
    chatStatusBadge.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle";
    chatStatusBadge.innerHTML = `<span class="status-dot ended"></span> Ended`;

    navSessionStatus.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle";
    navSessionStatus.innerHTML = `<span class="status-dot ended"></span> Ended`;

    endedBanner.classList.remove("d-none");
    inputArea.classList.add("d-none");
    btnEndSession.classList.add("d-none");
  } else {
    chatStatusBadge.className = "badge bg-success-subtle text-success border border-success-subtle";
    chatStatusBadge.innerHTML = `<span class="status-dot active"></span> Active`;

    navSessionStatus.className = "badge bg-success-subtle text-success border border-success-subtle";
    navSessionStatus.innerHTML = `<span class="status-dot active"></span> Active Session`;

    endedBanner.classList.add("d-none");
    inputArea.classList.remove("d-none");
    btnEndSession.classList.remove("d-none");

    document.getElementById("userMessageInput").disabled = false;
    document.getElementById("btnSendMessage").disabled = false;
  }
}

// Render message history
function renderMessageHistory(messages) {
  const chatMessagesEl = document.getElementById("chatMessages");
  chatMessagesEl.innerHTML = "";

  if (messages.length === 0) {
    chatMessagesEl.innerHTML = `
      <div class="text-center py-5 text-muted">
        <i class="bi bi-chat-heart fs-1 text-primary-subtle d-block mb-2"></i>
        <h6>Welcome to Support!</h6>
        <p class="small">How can we assist you with ${currentSession ? currentSession.product : "our software"} today?</p>
      </div>
    `;
    return;
  }

  messages.forEach(msg => appendMessage(msg));
}

// Append single message to chat
function appendMessage(msg) {
  const chatMessagesEl = document.getElementById("chatMessages");
  const isUser = msg.sender === "user";

  const row = document.createElement("div");
  row.className = `message-row ${isUser ? "user" : "bot"}`;

  // Avatar
  const avatar = document.createElement("div");
  avatar.className = "message-avatar shadow-sm";
  avatar.innerHTML = isUser ? `<i class="bi bi-person-fill"></i>` : `<i class="bi bi-robot"></i>`;

  // Content wrapper
  const content = document.createElement("div");
  content.className = "message-content";

  // Bubble
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  if (isUser) {
    bubble.textContent = msg.message;
  } else {
    // Parse Markdown safely
    const rawHtml = window.marked ? marked.parse(msg.message) : msg.message;
    const cleanHtml = window.DOMPurify ? DOMPurify.sanitize(rawHtml) : rawHtml;
    bubble.innerHTML = cleanHtml;
  }

  content.appendChild(bubble);

  // RAG Sources Accordion (Bot only)
  if (!isUser && msg.rag_sources && msg.rag_sources.length > 0) {
    const sourcesWrapper = renderSourcesAccordion(msg.rag_sources, msg.id || Date.now());
    content.appendChild(sourcesWrapper);
  }

  // Timestamp
  const timeEl = document.createElement("div");
  timeEl.className = "message-time";
  const dateObj = msg.timestamp ? new Date(msg.timestamp) : new Date();
  timeEl.textContent = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  content.appendChild(timeEl);

  row.appendChild(avatar);
  row.appendChild(content);
  chatMessagesEl.appendChild(row);

  // Scroll to bottom
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

// Render collapsible RAG Sources badge & card
function renderSourcesAccordion(sources, id) {
  const accordionId = `sources-acc-${id}`;
  const collapseId = `sources-col-${id}`;

  const wrapper = document.createElement("div");
  wrapper.className = "rag-sources-wrapper";

  let sourcesHtml = "";
  sources.forEach(s => {
    const simPct = Math.round((s.similarity_score || 0) * 100);
    sourcesHtml += `
      <div class="rag-source-card">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="fw-bold text-primary"><i class="bi bi-file-earmark-text me-1"></i> [${escapeHtml(s.ticket_code)}] ${escapeHtml(s.category)}</span>
          <span class="badge bg-primary-subtle text-primary border border-primary-subtle score-badge">
            ${simPct}% Match
          </span>
        </div>
        <div class="text-muted small mb-1">
          <strong>Historical Query:</strong> "${escapeHtml(s.customer_query)}"
        </div>
        <div class="small text-dark">
          <strong>Verified Solution:</strong> ${escapeHtml(s.resolution_summary)}
        </div>
      </div>
    `;
  });

  wrapper.innerHTML = `
    <div class="accordion accordion-flush" id="${accordionId}">
      <div class="accordion-item border-0 bg-transparent">
        <h2 class="accordion-header">
          <button class="accordion-button collapsed py-1 px-2 rounded-2 text-muted small bg-light border" 
                  type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}">
            <i class="bi bi-journal-bookmark-fill text-primary me-2"></i>
            <span>Grounding Sources: <strong>${sources.length} historical tickets retrieved</strong></span>
          </button>
        </h2>
        <div id="${collapseId}" class="accordion-collapse collapse mt-2" data-bs-parent="#${accordionId}">
          <div class="accordion-body p-0">
            ${sourcesHtml}
          </div>
        </div>
      </div>
    </div>
  `;

  return wrapper;
}

// Show/hide typing indicator
function showTypingIndicator(show) {
  const indicator = document.getElementById("typingIndicator");
  const chatMessagesEl = document.getElementById("chatMessages");
  if (show) {
    indicator.classList.remove("d-none");
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  } else {
    indicator.classList.add("d-none");
  }
}

// Open Past Sessions Modal
async function openHistoryModal() {
  const modal = new bootstrap.Modal(document.getElementById("historyModal"));
  modal.show();

  const container = document.getElementById("historyListContainer");
  container.innerHTML = `<div class="p-4 text-center text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Loading past sessions...</div>`;

  try {
    const res = await fetch("/api/sessions");
    const data = await res.json();
    const sessions = data.sessions || [];

    if (sessions.length === 0) {
      container.innerHTML = `<div class="p-4 text-center text-muted">No past conversations recorded yet.</div>`;
      return;
    }

    container.innerHTML = "";
    sessions.forEach(s => {
      const isCurrent = currentSession && currentSession.session_id === s.session_id;
      const isEnded = s.status === "ended";
      const item = document.createElement("div");
      item.className = `list-group-item list-group-item-action p-3 ${isCurrent ? 'bg-primary-subtle' : ''}`;

      const dateStr = s.created_at ? new Date(s.created_at).toLocaleString() : "N/A";

      item.innerHTML = `
        <div class="d-flex w-100 justify-content-between align-items-center mb-1">
          <h6 class="mb-0 fw-bold">
            ${escapeHtml(s.customer_name)} 
            <small class="text-muted fw-normal">(${escapeHtml(s.customer_email)})</small>
          </h6>
          <div>
            <span class="badge ${isEnded ? 'bg-secondary' : 'bg-success'} me-1">${s.status}</span>
            <span class="badge bg-primary">${escapeHtml(s.product)}</span>
          </div>
        </div>
        <p class="mb-1 text-muted small text-truncate">
          ${s.last_message ? escapeHtml(s.last_message) : "<em>No messages yet</em>"}
        </p>
        <div class="d-flex justify-content-between align-items-center text-muted small">
          <span><i class="bi bi-calendar3 me-1"></i> ${dateStr} &bull; ${s.message_count || 0} messages</span>
          <button class="btn btn-sm btn-outline-primary py-0 px-2 btn-load-session" data-id="${s.session_id}">
            View Conversation &rarr;
          </button>
        </div>
      `;

      item.querySelector(".btn-load-session").addEventListener("click", () => {
        modal.hide();
        loadSessionById(s.session_id);
      });

      container.appendChild(item);
    });
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-center text-danger">Failed to load sessions: ${escapeHtml(err.message)}</div>`;
  }
}

// Load a specific session by ID
async function loadSessionById(sessionId) {
  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    const data = await res.json();
    if (!res.ok || !data.session) {
      alert("Could not load session.");
      return;
    }
    currentSession = data.session;
    if (currentSession.status === "active") {
      localStorage.setItem("omni_active_session_id", currentSession.session_id);
    } else {
      localStorage.removeItem("omni_active_session_id");
    }
    switchToChatView(currentSession);
    renderMessageHistory(data.messages || []);
  } catch (err) {
    alert("Error loading session: " + err.message);
  }
}

// Open Knowledge Base Explorer Modal
let allKBTickets = [];
async function openKBModal() {
  const modal = new bootstrap.Modal(document.getElementById("kbModal"));
  modal.show();
  await loadKBTickets();
}

async function loadKBTickets() {
  const productFilter = document.getElementById("kbProductFilter").value;
  const container = document.getElementById("kbCardsContainer");
  const countBadge = document.getElementById("kbCountBadge");

  container.innerHTML = `<div class="col-12 text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Loading knowledge base...</div>`;

  try {
    const url = productFilter ? `/api/historical-tickets?product=${encodeURIComponent(productFilter)}` : "/api/historical-tickets";
    const res = await fetch(url);
    const data = await res.json();
    allKBTickets = data.tickets || [];

    countBadge.textContent = `${allKBTickets.length} Tickets`;

    if (allKBTickets.length === 0) {
      container.innerHTML = `<div class="col-12 text-center py-4 text-muted">No historical tickets found.</div>`;
      return;
    }

    container.innerHTML = "";
    allKBTickets.forEach(t => {
      const col = document.createElement("div");
      col.className = "col-md-6 col-lg-4";
      col.innerHTML = `
        <div class="card kb-card border shadow-sm rounded-3 p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-primary text-uppercase">${escapeHtml(t.ticket_code)}</span>
            <span class="badge bg-secondary-subtle text-secondary">${escapeHtml(t.category)}</span>
          </div>
          <h6 class="fw-bold text-dark mb-1">${escapeHtml(t.product)}</h6>
          <div class="text-muted small mb-2 fst-italic">
            "${escapeHtml(t.customer_query)}"
          </div>
          <div class="small text-success-emphasis bg-success-subtle p-2 rounded-2 mb-2">
            <strong>Key Resolution:</strong> ${escapeHtml(t.resolution_summary)}
          </div>
          <details class="small mt-auto">
            <summary class="text-primary cursor-pointer">View Full Verified Response</summary>
            <div class="p-2 bg-light rounded mt-1 border text-secondary" style="white-space: pre-line; max-height: 150px; overflow-y: auto;">
              ${escapeHtml(t.support_response)}
            </div>
          </details>
        </div>
      `;
      container.appendChild(col);
    });
  } catch (err) {
    container.innerHTML = `<div class="col-12 text-center py-4 text-danger">Failed to load tickets: ${escapeHtml(err.message)}</div>`;
  }
}

// Download session transcript as a text file
async function exportTranscript() {
  if (!currentSession) return;

  try {
    const res = await fetch(`/api/sessions/${currentSession.session_id}`);
    const data = await res.json();
    const messages = data.messages || [];

    let text = `======================================================\n`;
    text += `SUPPORT CONVERSATION TRANSCRIPT\n`;
    text += `======================================================\n`;
    text += `Session ID     : ${currentSession.session_id}\n`;
    text += `Customer Name  : ${currentSession.customer_name}\n`;
    text += `Customer Email : ${currentSession.customer_email}\n`;
    text += `Product        : ${currentSession.product}\n`;
    text += `Status         : ${currentSession.status}\n`;
    text += `Started At     : ${currentSession.created_at}\n`;
    text += `Ended At       : ${currentSession.ended_at || "In Progress"}\n`;
    text += `======================================================\n\n`;

    messages.forEach((m, idx) => {
      const sender = m.sender === "user" ? currentSession.customer_name : "OmniSupport AI";
      const time = m.timestamp ? new Date(m.timestamp).toLocaleString() : "";
      text += `[${time}] ${sender}:\n`;
      text += `${m.message}\n`;
      if (m.rag_sources && m.rag_sources.length > 0) {
        text += `   [RAG Sources: ${m.rag_sources.map(s => s.ticket_code).join(", ")}]\n`;
      }
      text += `\n------------------------------------------------------\n\n`;
    });

    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript-${currentSession.product.replace(/\s+/g, "_")}-${currentSession.session_id.substring(0, 8)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Failed to export transcript: " + err.message);
  }
}

// Helper to escape HTML characters
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

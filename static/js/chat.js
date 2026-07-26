// ============================================================
// 消息流渲染：用户气泡 / AI 直排 Markdown / Agent 步骤 / 来源引用
// ============================================================

const messagesEl = document.getElementById("messages");
const emptyEl = document.getElementById("empty-state");
const scrollEl = document.getElementById("chat-scroll");

/** LLM 输出不可信：marked 渲染后必须经 DOMPurify 消毒再插入（防 XSS） */
function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ""));
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

export function clearMessages() {
  messagesEl.innerHTML = "";
  emptyEl.hidden = false;
}

function hideEmpty() {
  emptyEl.hidden = true;
}

export function scrollToBottom(force = false) {
  const nearBottom = scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight < 120;
  if (force || nearBottom) scrollEl.scrollTop = scrollEl.scrollHeight;
}

// ---------- 各类消息 ----------

export function addUserMessage(text) {
  hideEmpty();
  const el = document.createElement("div");
  el.className = "msg msg-user";
  el.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  messagesEl.appendChild(el);
  scrollToBottom(true);
}

export function addSystemMessage(text) {
  hideEmpty();
  const el = document.createElement("div");
  el.className = "msg msg-system";
  el.textContent = text;
  messagesEl.appendChild(el);
  scrollToBottom();
}

/** 人工客服消息（工单频道） */
export function addHumanMessage(senderName, text) {
  hideEmpty();
  const el = document.createElement("div");
  el.className = "msg msg-human";
  el.innerHTML = `
    <div class="role-line"><span class="role-tag">人工客服 · ${escapeHtml(senderName)}</span></div>
    <div class="md">${renderMarkdown(text)}</div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
}

function sourcesHtml(sources) {
  if (!sources?.length) return "";
  const items = sources.map((s) => `
    <div class="source-item">
      <div class="src-head"><span>${escapeHtml(s.filename)}</span><span>相关度 ${Math.round((s.score || 0) * 100)}%</span></div>
      <div class="src-snippet">${escapeHtml(s.snippet)}…</div>
    </div>`).join("");
  return `
    <details class="sources">
      <summary>引用了 ${sources.length} 个知识库片段</summary>
      ${items}
    </details>`;
}

/** 历史 AI 消息（一次性渲染） */
export function addAssistantMessage(text, sources) {
  hideEmpty();
  const el = document.createElement("div");
  el.className = "msg msg-assistant";
  el.innerHTML = `
    <div class="role-line"><span class="role-tag">AI</span></div>
    <div class="md">${renderMarkdown(text)}</div>
    ${sourcesHtml(sources)}`;
  messagesEl.appendChild(el);
}

// ---------- 流式 AI 消息 ----------

const STEP_FLOW = { classify: "识别意图", retrieve: "检索知识库", escalate: "创建工单", generate: "生成回答" };

/** 创建一条流式渲染中的 AI 消息，返回控制器。 */
export function createStreamingMessage() {
  hideEmpty();
  const el = document.createElement("div");
  el.className = "msg msg-assistant";
  el.innerHTML = `
    <div class="role-line">
      <span class="role-tag">AI</span>
      <span class="agent-steps"></span>
    </div>
    <div class="md streaming-cursor"></div>
    <div class="sources-slot"></div>`;
  messagesEl.appendChild(el);
  scrollToBottom(true);

  const stepsEl = el.querySelector(".agent-steps");
  const mdEl = el.querySelector(".md");
  const slotEl = el.querySelector(".sources-slot");
  let text = "";
  let steps = [];
  let sources = [];
  let renderPending = false;

  const renderSteps = () => {
    stepsEl.innerHTML = steps.map((s, i) => {
      const running = i === steps.length - 1 && !text;
      return `${i ? '<span class="sep">›</span>' : ""}<span class="step ${running ? "running" : "done"}">${STEP_FLOW[s] || s}</span>`;
    }).join("");
  };

  const renderText = () => {
    if (renderPending) return;
    renderPending = true;
    requestAnimationFrame(() => {
      renderPending = false;
      mdEl.innerHTML = renderMarkdown(text);
      scrollToBottom();
    });
  };

  return {
    addStep(step) {
      if (!steps.includes(step)) { steps.push(step); renderSteps(); }
    },
    addToken(token) {
      text += token;
      renderSteps();
      renderText();
    },
    setSources(list) { sources = list; },
    fail(message) {
      text = text || "";
      mdEl.classList.remove("streaming-cursor");
      mdEl.innerHTML = renderMarkdown(text) +
        `<p style="color:var(--danger)">⚠ ${escapeHtml(message)}</p>`;
    },
    finish() {
      mdEl.classList.remove("streaming-cursor");
      mdEl.innerHTML = renderMarkdown(text);
      if (sources.length) slotEl.innerHTML = sourcesHtml(sources);
      renderSteps();
      scrollToBottom();
      return text;
    },
    get isEmpty() { return !text; },
  };
}

const AGENT_META = {
  incident_detector: {
    title: "网络事故检测",
    shortTitle: "事故检测",
    icon: "检",
    description: "分析本地 LTE KPI，识别异常并在确认后创建 Incident。",
    welcome: "开始检测网络异常",
    welcomeDescription:
      "系统将读取本地 DuckDB 中的 KPI 数据，列出潜在 Incident，并在写入前征求你的确认。",
    placeholder: "例如：检查是否存在新的网络事故…",
    suggestions: [
      "检查是否存在新的 Incident，并列出异常 KPI。",
      "扫描 LTE KPI 数据，告诉我最需要关注的异常。",
    ],
  },
  root_cause_analysis: {
    title: "根因分析（RCA）",
    shortTitle: "根因分析",
    icon: "析",
    description: "围绕指定 Incident 完成证据驱动的 RCA 与报告生成。",
    welcome: "开始进行 Root Cause Analysis",
    welcomeDescription:
      "请输入 Incident ID。系统将检索规则、Cell Trace、历史 Incident 和本地资料，并生成中文 RCA 报告。",
    placeholder: "例如：分析 Incident 79996b30-…",
    suggestions: [
      "请分析 Incident ID：",
      "对指定 Incident 执行完整 RCA，但不要执行建议动作。",
    ],
  },
};

const state = {
  availableApps: [],
  appName: null,
  userId: "local-operator",
  sessionId: null,
  busy: false,
  abortController: null,
  stopRequested: false,
  currentRunView: null,
  conversations: [],
  renamingSessionId: null,
  deletingSessionId: null,
  historyRequestVersion: 0,
  deletedSessionIds: new Set(),
};

const elements = {
  agentNav: document.querySelector("#agent-nav"),
  agentTitle: document.querySelector("#current-agent-title"),
  agentDescription: document.querySelector("#current-agent-description"),
  chat: document.querySelector("#chat"),
  welcome: document.querySelector("#welcome"),
  welcomeTitle: document.querySelector("#welcome-title"),
  welcomeDescription: document.querySelector("#welcome-description"),
  quickActions: document.querySelector("#quick-actions"),
  composer: document.querySelector("#composer"),
  input: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-button"),
  stopButton: document.querySelector("#stop-button"),
  newSession: document.querySelector("#new-session"),
  runtimeStatus: document.querySelector("#runtime-status"),
  messageTemplate: document.querySelector("#message-template"),
  conversationHistory: document.querySelector("#conversation-history"),
  refreshHistory: document.querySelector("#refresh-history"),
  renameDialog: document.querySelector("#rename-dialog"),
  renameForm: document.querySelector("#rename-form"),
  renameInput: document.querySelector("#conversation-title"),
  renameClose: document.querySelector("#rename-close"),
  renameCancel: document.querySelector("#rename-cancel"),
  deleteDialog: document.querySelector("#delete-dialog"),
  deleteDescription: document.querySelector("#delete-description"),
  deleteClose: document.querySelector("#delete-close"),
  deleteCancel: document.querySelector("#delete-cancel"),
  deleteConfirm: document.querySelector("#delete-confirm"),
};

function createId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sessionsPath(sessionId = "", appName = state.appName) {
  const base = `/apps/${encodeURIComponent(appName)}/users/${encodeURIComponent(state.userId)}/sessions`;
  return sessionId ? `${base}/${encodeURIComponent(sessionId)}` : base;
}

function cacheBustedUrl(path) {
  const url = new URL(path, window.location.origin);
  url.searchParams.set("_history_refresh", `${Date.now()}-${state.historyRequestVersion}`);
  return url;
}

const FRESH_FETCH_OPTIONS = {
  cache: "no-store",
  headers: {
    "Cache-Control": "no-cache, no-store",
    Pragma: "no-cache",
  },
};

function makeConversationTitle(text) {
  const compact = String(text || "")
    .replace(/[`#*_<>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!compact) return "新对话";
  return compact.length > 28 ? `${compact.slice(0, 28)}…` : compact;
}

function conversationTitle(session) {
  return session?.state?.conversation_title || "未命名对话";
}

function formatConversationTime(seconds) {
  if (!seconds) return "尚无消息";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(seconds * 1000));
}

function setRuntimeStatus(text, mode = "ready") {
  elements.runtimeStatus.classList.toggle("busy", mode === "busy");
  elements.runtimeStatus.classList.toggle("error", mode === "error");
  elements.runtimeStatus.querySelector("span:last-child").textContent = text;
}

function setBusy(busy, cancellable = busy) {
  state.busy = busy;
  elements.input.disabled = busy;
  elements.sendButton.disabled = busy;
  elements.sendButton.hidden = busy && cancellable;
  elements.stopButton.hidden = !busy || !cancellable;
  elements.stopButton.disabled = false;
  elements.newSession.disabled = busy;
  if (busy) setRuntimeStatus("DeepSeek 正在分析，请稍候…", "busy");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderInline(value) {
  let html = escapeHtml(value);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g, (_all, label, url) => {
    return `<a href="${url}" target="_blank" rel="noreferrer">${label}</a>`;
  });
  return html;
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replaceAll("\r\n", "\n").split("\n");
  const html = [];
  let listType = null;
  let tableRows = [];

  const closeList = () => {
    if (listType) html.push(`</${listType}>`);
    listType = null;
  };

  const flushTable = () => {
    if (!tableRows.length) return;
    const rows = tableRows.filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)));
    if (rows.length) {
      html.push("<table>");
      rows.forEach((row, index) => {
        const tag = index === 0 ? "th" : "td";
        html.push(`<tr>${row.map((cell) => `<${tag}>${renderInline(cell.trim())}</${tag}>`).join("")}</tr>`);
      });
      html.push("</table>");
    }
    tableRows = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (/^\|.*\|$/.test(line.trim())) {
      closeList();
      tableRows.push(line.trim().slice(1, -1).split("|"));
      continue;
    }
    flushTable();

    if (!line.trim()) {
      closeList();
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }
    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      if (listType !== "ul") {
        closeList();
        listType = "ul";
        html.push("<ul>");
      }
      html.push(`<li>${renderInline(unordered[1])}</li>`);
      continue;
    }
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      if (listType !== "ol") {
        closeList();
        listType = "ol";
        html.push("<ol>");
      }
      html.push(`<li>${renderInline(ordered[1])}</li>`);
      continue;
    }
    closeList();
    html.push(`<p>${renderInline(line)}</p>`);
  }
  flushTable();
  closeList();
  return html.join("");
}

function addMessage(role, text, { typing = false } = {}) {
  elements.welcome?.remove();
  const fragment = elements.messageTemplate.content.cloneNode(true);
  const message = fragment.querySelector(".message");
  const avatar = fragment.querySelector(".message-avatar");
  const roleLabel = fragment.querySelector(".message-role");
  const content = fragment.querySelector(".message-content");
  message.classList.add(role);
  avatar.textContent = role === "user" ? "我" : "AI";
  roleLabel.textContent = role === "user" ? "你" : "智能运维助手";
  if (typing) {
    message.dataset.typing = "true";
    content.innerHTML = '<span class="typing" aria-label="正在分析"><i></i><i></i><i></i></span>';
  } else {
    content.innerHTML = renderMarkdown(text);
  }
  elements.chat.appendChild(fragment);
  elements.chat.scrollTop = elements.chat.scrollHeight;
  return elements.chat.lastElementChild;
}

const AGENT_LABELS = {
  incident_detector: "事故检测 Agent",
  root_cause_analysis: "RCA 主 Agent",
  root_cause_analyst: "RCA 主 Agent",
  incident_retriever_agent: "Incident 检索 Agent",
  processing_rules_retriever: "RCA 规则检索 Agent",
  instruction_generator_agent: "分析指令生成 Agent",
  analyzer_agent: "证据分析 Agent",
  severity_classifier_agent: "严重程度判断 Agent",
  external_documentation_retriever_agent: "外部资料检索 Agent",
  internal_documentation_retriever_agent: "内部资料检索 Agent",
  prior_incidents_search_agent: "历史 Incident 检索 Agent",
  report_generator_agent: "报告生成 Agent",
  action_executor_agent: "建议动作 Agent",
};

const TOOL_LABELS = {
  get_potential_incidents: "查询 KPI 异常并生成候选 Incident",
  create_new_incident: "保存用户确认的 Incident",
  get_incident_info: "读取 Incident 详细信息",
  processing_rules_retriever: "匹配本地 RCA 规则",
  instruction_generator_agent: "根据规则生成分析步骤",
  get_cell_trace_statistics: "统计匹配时间窗口内的 Cell Trace",
  get_uplink_rssi_level: "读取上行链路 RSSI",
  get_uplink_configuration: "读取上行链路配置",
  initiate_uplink_configuration_adjustment: "执行模拟上行配置调整",
  save_analysis: "记录阶段性分析证据",
  update_severity_level: "更新 RCA 严重程度",
  external_documentation_retriever_agent: "检索外部参考资料",
  internal_documentation_retriever_agent: "检索本地运维文档",
  prior_incidents_search_agent: "检索相似历史 Incident",
  report_generator_agent: "生成 RCA 报告",
  update_incident: "保存最终 RCA 报告",
  transfer_to_agent: "切换到专业子 Agent",
};

function createRunView() {
  const message = addMessage("assistant", "");
  const content = message.querySelector(".message-content");
  content.innerHTML = `
    <details class="execution-trace" open>
      <summary>
        <span>公开执行过程</span>
        <span class="trace-state">执行中</span>
      </summary>
      <ol class="execution-steps"></ol>
      <p class="trace-note">展示 Agent 阶段、工具调用和状态，不展示模型隐藏推理。</p>
    </details>
    <div class="answer-output" aria-live="polite"></div>
  `;
  return {
    message,
    steps: content.querySelector(".execution-steps"),
    traceState: content.querySelector(".trace-state"),
    answer: content.querySelector(".answer-output"),
    toolSteps: new Map(),
    answerText: "",
    partialText: "",
    lastAuthor: null,
    answerStarted: false,
  };
}

function addExecutionStep(view, text, mode = "done") {
  const item = document.createElement("li");
  item.className = mode;
  item.innerHTML = `<span class="step-marker" aria-hidden="true"></span><span>${escapeHtml(text)}</span>`;
  view.steps.appendChild(item);
  elements.chat.scrollTop = elements.chat.scrollHeight;
  return item;
}

function setTraceState(view, text, mode = "done") {
  view.traceState.textContent = text;
  view.traceState.className = `trace-state ${mode}`;
}

function toolLabel(name, args = {}) {
  if (name === "transfer_to_agent") {
    const target = args.agent_name || args.agentName;
    if (target) return `转交给${AGENT_LABELS[target] || target}`;
  }
  return TOOL_LABELS[name] || `调用工具：${name}`;
}

function responseSummary(name, response) {
  if (name === "get_potential_incidents" && Array.isArray(response?.incidents)) {
    return `完成：发现 ${response.incidents.length} 个候选 Incident`;
  }
  if (name === "get_cell_trace_statistics" && Array.isArray(response?.cell_trace_statistics)) {
    return `完成：获得 ${response.cell_trace_statistics.length} 组 Cell Trace 统计`;
  }
  const status = response?.status;
  const statuses = {
    success: "完成",
    disabled: "已跳过（功能未启用）",
    "not found": "完成，但未找到对应的 Incident",
    "no cell traces found": "完成，但未找到匹配的 Cell Trace",
    "no similar incidents found": "完成，但未找到相似历史 Incident",
    failed: "未完成",
    error: "执行失败",
  };
  return statuses[status] || "完成";
}

function appendAnswer(view, text, partial) {
  if (!text) return;
  if (!view.answerStarted) {
    addExecutionStep(view, "开始生成面向用户的答案", "running");
    view.answerStarted = true;
  }
  if (partial) {
    view.partialText += text;
  } else if (view.partialText) {
    const complete = text.startsWith(view.partialText) ? text : `${view.partialText}${text}`;
    view.answerText = joinAnswerSegments(view.answerText, complete);
    view.partialText = "";
  } else {
    view.answerText = joinAnswerSegments(view.answerText, text);
  }
  view.answer.innerHTML = renderMarkdown(
    joinAnswerSegments(view.answerText, view.partialText),
  );
  elements.chat.scrollTop = elements.chat.scrollHeight;
}

function joinAnswerSegments(current, next) {
  if (!current) return next || "";
  if (!next) return current;
  if (current.endsWith("\n") || next.startsWith("\n")) return `${current}${next}`;
  return `${current}\n\n${next}`;
}

function handleAgentEvent(view, event) {
  if (event?.error) throw new Error(event.error);
  const isUserContent = event?.content?.role === "user";

  const author = event?.author;
  if (!isUserContent && author && author !== view.lastAuthor) {
    addExecutionStep(view, `进入${AGENT_LABELS[author] || author}`, "done");
    view.lastAuthor = author;
  }

  for (const part of event?.content?.parts || []) {
    if (part?.thought) continue;
    if (part?.text && !isUserContent) {
      appendAnswer(view, part.text, event.partial === true);
    }

    const call = part?.functionCall;
    if (call && event.partial !== true) {
      const item = addExecutionStep(view, toolLabel(call.name, call.args), "running");
      if (call.id) view.toolSteps.set(call.id, item);
    }

    const result = part?.functionResponse;
    if (result && event.partial !== true) {
      const item = result.id ? view.toolSteps.get(result.id) : null;
      const summary = `${toolLabel(result.name)}：${responseSummary(result.name, result.response)}`;
      if (item) {
        item.className = "done";
        item.querySelector("span:last-child").textContent = summary;
      } else {
        addExecutionStep(view, summary, "done");
      }
    }
  }
}

async function consumeSse(response, onEvent) {
  if (!response.body) throw new Error("浏览器不支持流式响应");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const consumeBlock = (block) => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data || data === "[DONE]") return;
    onEvent(JSON.parse(data));
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";
    blocks.forEach(consumeBlock);
    if (done) break;
  }
  if (buffer.trim()) consumeBlock(buffer);
}

function renderAgentNavigation() {
  elements.agentNav.replaceChildren();
  for (const appName of state.availableApps) {
    const meta = AGENT_META[appName];
    if (!meta) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "agent-button";
    button.dataset.app = appName;
    button.innerHTML = `
      <span class="agent-icon">${meta.icon}</span>
      <span><strong>${meta.shortTitle}</strong><span>${appName}</span></span>
    `;
    button.addEventListener("click", () => selectAgent(appName));
    elements.agentNav.appendChild(button);
  }
}

function renderConversationHistory() {
  elements.conversationHistory.replaceChildren();
  if (!state.conversations.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = "当前 Agent 还没有历史对话";
    elements.conversationHistory.appendChild(empty);
    return;
  }

  for (const session of state.conversations) {
    const item = document.createElement("div");
    item.className = "conversation-item";
    item.classList.toggle("active", session.id === state.sessionId);

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "conversation-open";
    openButton.title = conversationTitle(session);
    const title = document.createElement("strong");
    title.textContent = conversationTitle(session);
    const time = document.createElement("span");
    time.textContent = formatConversationTime(session.lastUpdateTime);
    openButton.append(title, time);
    openButton.addEventListener("click", () => selectConversation(session.id));

    const controls = document.createElement("div");
    controls.className = "conversation-controls";
    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.className = "conversation-control";
    renameButton.setAttribute("aria-label", `重命名对话：${conversationTitle(session)}`);
    renameButton.title = "重命名";
    renameButton.textContent = "改";
    renameButton.addEventListener("click", () => openRenameDialog(session));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "conversation-control danger";
    deleteButton.setAttribute("aria-label", `删除对话：${conversationTitle(session)}`);
    deleteButton.title = "删除";
    deleteButton.textContent = "删";
    deleteButton.addEventListener("click", () => openDeleteDialog(session));

    controls.append(renameButton, deleteButton);
    item.append(openButton, controls);
    elements.conversationHistory.appendChild(item);
  }
}

async function loadConversations(appName = state.appName) {
  if (!appName) return;
  const requestVersion = ++state.historyRequestVersion;
  const response = await fetch(
    cacheBustedUrl(sessionsPath("", appName)),
    FRESH_FETCH_OPTIONS,
  );
  if (!response.ok) throw new Error("无法读取历史对话");
  const sessions = await response.json();
  if (state.appName !== appName || requestVersion !== state.historyRequestVersion) {
    return;
  }

  const serverSessionIds = new Set(sessions.map((session) => session.id));
  for (const sessionId of state.deletedSessionIds) {
    if (!serverSessionIds.has(sessionId)) state.deletedSessionIds.delete(sessionId);
  }

  state.conversations = sessions
    .filter((session) => !state.deletedSessionIds.has(session.id))
    .sort(
    (left, right) => (right.lastUpdateTime || 0) - (left.lastUpdateTime || 0),
    );
  renderConversationHistory();
}

function finalizeHistoricalView(view) {
  if (!view) return;
  if (view.partialText) {
    view.answerText = joinAnswerSegments(view.answerText, view.partialText);
    view.partialText = "";
    view.answer.innerHTML = renderMarkdown(view.answerText);
  }
  view.steps.querySelectorAll("li.running").forEach((item) => {
    item.className = "done";
  });
  setTraceState(view, "历史记录", "done");
}

function renderSessionHistory(session) {
  elements.chat.replaceChildren();
  elements.welcome = null;
  let runView = null;
  let visibleMessages = 0;

  for (const event of session.events || []) {
    const parts = event?.content?.parts || [];
    const hasFunctionResponse = parts.some((part) => part?.functionResponse);
    const userText = parts
      .filter((part) => part?.text && !part?.thought)
      .map((part) => part.text)
      .join("");
    const isUserMessage =
      event?.content?.role === "user" && userText && !hasFunctionResponse;

    if (isUserMessage) {
      finalizeHistoricalView(runView);
      runView = null;
      addMessage("user", userText);
      visibleMessages += 1;
      continue;
    }

    const isVisibleAgentEvent = parts.some(
      (part) =>
        (part?.text && !part?.thought) ||
        part?.functionCall ||
        part?.functionResponse,
    );
    if (!isVisibleAgentEvent) continue;
    if (!runView) runView = createRunView();
    handleAgentEvent(runView, { ...event, partial: false });
    visibleMessages += 1;
  }

  finalizeHistoricalView(runView);
  if (!visibleMessages) renderWelcome();
  elements.chat.scrollTop = elements.chat.scrollHeight;
}

async function selectConversation(sessionId) {
  if (state.busy || !state.appName) return;
  setBusy(true, false);
  setRuntimeStatus("正在读取历史对话…", "busy");
  try {
    const response = await fetch(sessionsPath(sessionId));
    if (!response.ok) throw new Error("历史对话不存在或已经删除");
    const session = await response.json();
    state.sessionId = session.id;
    renderConversationHistory();
    renderSessionHistory(session);
    setRuntimeStatus("历史对话已加载");
  } catch (error) {
    setRuntimeStatus("读取历史对话失败", "error");
    addMessage("assistant", `无法读取历史对话：${error.message}`);
  } finally {
    setBusy(false);
    elements.input.focus();
  }
}

function openRenameDialog(session) {
  if (state.busy) return;
  state.renamingSessionId = session.id;
  elements.renameInput.value = conversationTitle(session);
  elements.renameDialog.showModal();
  elements.renameInput.focus();
  elements.renameInput.select();
}

function closeRenameDialog() {
  state.renamingSessionId = null;
  elements.renameDialog.close();
}

function openDeleteDialog(session) {
  if (state.busy) return;
  state.deletingSessionId = session.id;
  elements.deleteDescription.textContent = `“${conversationTitle(session)}”及其中的聊天消息将被永久删除。`;
  elements.deleteDialog.showModal();
}

function closeDeleteDialog() {
  state.deletingSessionId = null;
  elements.deleteDialog.close();
}

function renderWelcome() {
  const meta = AGENT_META[state.appName];
  const welcome = document.createElement("div");
  welcome.id = "welcome";
  welcome.className = "welcome-card";
  welcome.innerHTML = `
    <div class="welcome-icon" aria-hidden="true">${meta.icon}</div>
    <h2>${meta.welcome}</h2>
    <p>${meta.welcomeDescription}</p>
    <div class="quick-actions"></div>
  `;
  const actions = welcome.querySelector(".quick-actions");
  for (const suggestion of meta.suggestions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-action";
    button.textContent = suggestion;
    button.addEventListener("click", () => {
      elements.input.value = suggestion;
      resizeInput();
      elements.input.focus();
    });
    actions.appendChild(button);
  }
  elements.chat.replaceChildren(welcome);
  elements.welcome = welcome;
}

async function createSession(initialMessage = "") {
  const sessionId = createId();
  const response = await fetch(sessionsPath(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessionId,
      state: {
        conversation_title: makeConversationTitle(initialMessage),
        conversation_created_at: new Date().toISOString(),
      },
    }),
  });
  if (!response.ok) throw new Error("无法创建本地会话");
  const session = await response.json();
  state.sessionId = session.id;
  await loadConversations();
  return session;
}

async function selectAgent(appName) {
  if (state.busy || !AGENT_META[appName]) return;
  state.appName = appName;
  const meta = AGENT_META[appName];
  document.querySelectorAll(".agent-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.app === appName);
  });
  elements.agentTitle.textContent = meta.title;
  elements.agentDescription.textContent = meta.description;
  elements.input.placeholder = meta.placeholder;
  state.sessionId = null;
  state.conversations = [];
  renderWelcome();
  renderConversationHistory();
  setRuntimeStatus("正在读取历史对话…", "busy");
  try {
    await loadConversations();
    setRuntimeStatus("准备就绪");
  } catch (error) {
    setRuntimeStatus("历史对话读取失败", "error");
    addMessage("assistant", `无法读取历史对话：${error.message}`);
  }
}

async function sendMessage(text) {
  if (!text.trim() || state.busy || !state.appName) return;
  addMessage("user", text.trim());
  elements.input.value = "";
  resizeInput();
  setBusy(true);
  state.stopRequested = false;
  state.abortController = new AbortController();
  const runView = createRunView();
  state.currentRunView = runView;
  addExecutionStep(runView, "收到任务，正在建立执行上下文", "done");

  try {
    if (!state.sessionId) await createSession(text.trim());
    addExecutionStep(runView, "已连接本地 DuckDB 与 DeepSeek", "done");
    const response = await fetch("/run_sse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: state.abortController.signal,
      body: JSON.stringify({
        appName: state.appName,
        userId: state.userId,
        sessionId: state.sessionId,
        newMessage: {
          role: "user",
          parts: [{ text: text.trim() }],
        },
        streaming: true,
      }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `服务返回 HTTP ${response.status}`);
    }
    await consumeSse(response, (event) => handleAgentEvent(runView, event));
    if (runView.partialText) {
      runView.answerText = joinAnswerSegments(runView.answerText, runView.partialText);
      runView.partialText = "";
    }
    if (!runView.answerText.trim()) {
      runView.answerText = "操作已经完成，但 Agent 没有返回可显示的文字。";
      runView.answer.innerHTML = renderMarkdown(runView.answerText);
    }
    runView.steps.querySelectorAll("li.running").forEach((item) => {
      item.className = "done";
    });
    addExecutionStep(runView, "本次 Agent 执行完成", "done");
    setTraceState(runView, "已完成", "done");
    setRuntimeStatus("分析完成");
  } catch (error) {
    if (error.name === "AbortError" || state.stopRequested) {
      runView.steps.querySelectorAll("li.running").forEach((item) => {
        item.className = "stopped";
      });
      addExecutionStep(runView, "用户已中断本次执行", "stopped");
      setTraceState(runView, "已中断", "stopped");
      const visible = joinAnswerSegments(
        runView.answerText,
        runView.partialText,
      ).trim();
      runView.answer.innerHTML = renderMarkdown(
        `${visible}${visible ? "\n\n" : ""}回答已由你中断，以上内容可能不完整。`,
      );
      setRuntimeStatus("已中断，可以继续提问");
    } else {
      addExecutionStep(runView, `执行失败：${error.message}`, "stopped");
      setTraceState(runView, "失败", "stopped");
      runView.answer.innerHTML = renderMarkdown(
        `处理请求时出现问题：${error.message}\n\n请检查 API Key 和本地服务日志后重试。`,
      );
      setRuntimeStatus("处理失败，请检查服务状态", "error");
    }
  } finally {
    state.abortController = null;
    state.currentRunView = null;
    setBusy(false);
    try {
      await loadConversations();
    } catch (error) {
      console.warn("Unable to refresh conversation history", error);
    }
    if (!elements.runtimeStatus.classList.contains("error") && !state.stopRequested) {
      setRuntimeStatus("准备就绪");
    }
    elements.input.focus();
  }
}

function resizeInput() {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 160)}px`;
}

async function initialize() {
  try {
    const response = await fetch("/list-apps");
    if (!response.ok) throw new Error("无法读取 Agent 列表");
    const apps = await response.json();
    state.availableApps = apps.filter((appName) => AGENT_META[appName]);
    if (!state.availableApps.length) throw new Error("没有找到可用的业务 Agent");
    renderAgentNavigation();
    await selectAgent(state.availableApps[0]);
  } catch (error) {
    elements.agentTitle.textContent = "服务连接失败";
    elements.agentDescription.textContent = "请确认本地后端已经启动";
    setRuntimeStatus("无法连接本地服务", "error");
    addMessage("assistant", `页面初始化失败：${error.message}`);
  }
}

elements.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(elements.input.value);
});

elements.stopButton.addEventListener("click", () => {
  if (!state.busy || !state.abortController) return;
  state.stopRequested = true;
  elements.stopButton.disabled = true;
  setRuntimeStatus("正在中断 Agent 执行…", "busy");
  if (state.currentRunView) {
    addExecutionStep(state.currentRunView, "正在请求停止当前任务", "running");
  }
  state.abortController.abort();
});

elements.input.addEventListener("input", resizeInput);
elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

elements.newSession.addEventListener("click", () => {
  if (state.busy || !state.appName) return;
  state.sessionId = null;
  renderWelcome();
  renderConversationHistory();
  setRuntimeStatus("新对话已就绪，发送消息后自动保存");
});

elements.refreshHistory.addEventListener("click", async () => {
  if (state.busy || !state.appName) return;
  elements.refreshHistory.disabled = true;
  try {
    await loadConversations();
    setRuntimeStatus("历史对话已刷新");
  } catch (error) {
    setRuntimeStatus("历史对话刷新失败", "error");
  } finally {
    elements.refreshHistory.disabled = false;
  }
});

elements.renameForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const sessionId = state.renamingSessionId;
  const title = elements.renameInput.value.replace(/\s+/g, " ").trim();
  if (!sessionId || !title) return;
  const submitButton = elements.renameForm.querySelector('[type="submit"]');
  submitButton.disabled = true;
  try {
    const response = await fetch(sessionsPath(sessionId), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stateDelta: { conversation_title: title } }),
    });
    if (!response.ok) throw new Error("重命名失败");
    closeRenameDialog();
    await loadConversations();
    setRuntimeStatus("对话名称已保存");
  } catch (error) {
    setRuntimeStatus(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

elements.deleteConfirm.addEventListener("click", async () => {
  const sessionId = state.deletingSessionId;
  if (!sessionId) return;
  const appName = state.appName;
  elements.deleteConfirm.disabled = true;
  state.deletedSessionIds.add(sessionId);
  state.historyRequestVersion += 1;
  state.conversations = state.conversations.filter(
    (session) => session.id !== sessionId,
  );
  renderConversationHistory();
  try {
    const response = await fetch(cacheBustedUrl(sessionsPath(sessionId, appName)), {
      ...FRESH_FETCH_OPTIONS,
      method: "DELETE",
    });
    if (!response.ok) throw new Error("删除失败");

    const verificationResponse = await fetch(
      cacheBustedUrl(sessionsPath("", appName)),
      FRESH_FETCH_OPTIONS,
    );
    if (!verificationResponse.ok) throw new Error("无法核验删除结果");
    const remainingSessions = await verificationResponse.json();
    if (remainingSessions.some((session) => session.id === sessionId)) {
      throw new Error("服务端仍存在该会话，删除未生效");
    }

    const deletedCurrentSession = state.sessionId === sessionId;
    closeDeleteDialog();
    if (deletedCurrentSession) {
      state.sessionId = null;
      renderWelcome();
    }
    state.deletedSessionIds.delete(sessionId);
    await loadConversations(appName);
    setRuntimeStatus("历史对话已删除");
  } catch (error) {
    state.deletedSessionIds.delete(sessionId);
    try {
      await loadConversations(appName);
    } catch (reloadError) {
      console.warn("Unable to reload conversations after delete failure", reloadError);
    }
    setRuntimeStatus(error.message, "error");
  } finally {
    elements.deleteConfirm.disabled = false;
  }
});

elements.renameClose.addEventListener("click", closeRenameDialog);
elements.renameCancel.addEventListener("click", closeRenameDialog);
elements.deleteClose.addEventListener("click", closeDeleteDialog);
elements.deleteCancel.addEventListener("click", closeDeleteDialog);
elements.renameDialog.addEventListener("close", () => {
  state.renamingSessionId = null;
});
elements.deleteDialog.addEventListener("close", () => {
  state.deletingSessionId = null;
});

initialize();

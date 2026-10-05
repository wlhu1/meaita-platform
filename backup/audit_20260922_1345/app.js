/* ME-AITA 教师成长智能体 - 前端主逻辑（真实智谱大模型接入） */
(function () {
  "use strict";

  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  var dialog = $("#dialog"), dialogTitle = $("#dialogTitle"), dialogDesc = $("#dialogDesc"),
      dialogTiles = $("#dialogTiles"), dialogNote = $("#dialogNote"),
      ask = $("#ask"), chatCard = $("#chatCard"), historyEl = $("#chatHistory"),
      chatForm = $("#chatForm"), sendBtn = $("#sendBtn"),
      sessionSelect = $("#sessionSelect"), sessionBar = $("#sessionBar"),
      modelName = $("#modelName"), searchToggle = $("#searchToggle");
  var toastTimer = null;
  var currentSessionId = null;
  var streaming = false;
  var searchEnabled = false;
  var API = ""; // 同源相对路径

  /* ---------- 工具 ---------- */
  function notify(message) {
    var el = $("#toast");
    el.textContent = message;
    el.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("on"); }, 2600);
  }

  function esc(html) {
    return String(html).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* ---------- Markdown 渲染（marked + highlight + KaTeX） ---------- */
  var markedReady = typeof marked !== "undefined";
  if (markedReady) {
    marked.setOptions({ breaks: true, gfm: true });
  }

  function renderMarkdown(text) {
    if (!markedReady) {
      return esc(text).replace(/\n/g, "<br>");
    }
    // 先转义原始 HTML，避免模型输出注入
    var safe = esc(text);
    var html;
    try { html = marked.parse(safe); } catch (e) { html = esc(text).replace(/\n/g, "<br>"); }
    // 代码高亮
    var wrap = document.createElement("div");
    wrap.innerHTML = html;
    if (typeof hljs !== "undefined") {
      wrap.querySelectorAll("pre code").forEach(function (block) {
        try { hljs.highlightElement(block); } catch (e) { /* 忽略高亮失败 */ }
      });
    }
    // 数学公式
    if (typeof renderMathInElement === "function") {
      try {
        renderMathInElement(wrap, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false }
          ],
          throwOnError: false
        });
      } catch (e) { /* 忽略公式渲染失败 */ }
    }
    return wrap.innerHTML;
  }

  function appendBubble(text, kind, opts) {
    opts = opts || {};
    var el = document.createElement("div");
    el.className = "bubble " + kind;
    if (kind === "bot") {
      var md = document.createElement("div");
      md.className = "md-body";
      if (opts.raw) {
        md.textContent = text;
      } else {
        md.innerHTML = text === "" ? '<span class="typing"><i></i><i></i><i></i></span>' : renderMarkdown(text);
      }
      el.appendChild(md);
      if (opts.meta) {
        var meta = document.createElement("div");
        meta.className = "demo-label";
        meta.textContent = opts.meta;
        el.appendChild(meta);
      }
    } else {
      el.textContent = text;
    }
    historyEl.appendChild(el);
    historyEl.scrollTop = historyEl.scrollHeight;
    return el;
  }

  /* ---------- 会话管理 ---------- */
  function loadSessions(selectId) {
    return fetch(API + "api/sessions")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sessions = data.sessions || [];
        sessionSelect.replaceChildren();
        sessions.forEach(function (s) {
          var opt = document.createElement("option");
          opt.value = s.id;
          opt.textContent = s.title + (s.id === currentSessionId ? "" : "");
          sessionSelect.appendChild(opt);
        });
        if (sessions.length && !currentSessionId) {
          currentSessionId = sessions[0].id;
        }
        if (currentSessionId) sessionSelect.value = String(currentSessionId);
        if (!sessions.length) {
          return createSession("新会话");
        }
        return Promise.resolve(null);
      })
      .catch(function () {
        notify("无法连接后端服务，请确认已启动 启动智能体.bat");
      });
  }

  function createSession(title) {
    return fetch(API + "api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title || "新会话" })
    }).then(function (r) { return r.json(); }).then(function (data) {
      currentSessionId = data.session.id;
      loadSessions();
      return data.session;
    });
  }

  function switchSession(id) {
    currentSessionId = id;
    clearChat();
    fetch(API + "api/sessions/" + id + "/messages")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var msgs = data.messages || [];
        if (!msgs.length) return;
        chatCard.classList.add("has-history");
        msgs.forEach(function (m) {
          if (m.role === "user") appendBubble(m.content, "user");
          else appendBubble(m.content, "bot");
        });
      })
      .catch(function () { notify("读取历史记录失败"); });
  }

  function clearChat() {
    chatCard.classList.remove("has-history");
    historyEl.replaceChildren();
  }

  function deleteCurrentSession() {
    if (!currentSessionId) return;
    if (!confirm("确定删除当前会话及其全部对话记录吗？")) return;
    fetch(API + "api/sessions/" + currentSessionId, { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function () {
        currentSessionId = null;
        clearChat();
        loadSessions();
        notify("会话已删除");
      })
      .catch(function () { notify("删除失败"); });
  }

  /* ---------- 流式问答 ---------- */
  function sendMessage() {
    var q = ask.value.trim();
    if (!q || streaming) return;
    streaming = true;
    sendBtn.disabled = true;
    chatCard.classList.add("has-history");
    appendBubble(q, "user");
    ask.value = "";
    var botEl = appendBubble("", "bot", { raw: true });
    var mdEl = botEl.querySelector(".md-body");
    var fullText = "";

    var payload = {
      session_id: currentSessionId,
      message: q,
      search: searchEnabled
    };

    fetch(API + "api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
      body: JSON.stringify(payload)
    }).then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (j) {
          throw new Error(j.detail || ("HTTP " + resp.status));
        });
      }
      var reader = resp.body.getReader();
      var decoder = new TextDecoder("utf-8");
      var buffer = "";
      function pump() {
        return reader.read().then(function (result) {
          if (result.done) { finish(); return; }
          buffer += decoder.decode(result.value, { stream: true });
          var parts = buffer.split("\n\n");
          buffer = parts.pop();
          parts.forEach(handleEvent);
          return pump();
        });
      }
      function handleEvent(block) {
        var lines = block.split("\n");
        var dataLine = "";
        lines.forEach(function (l) {
          if (l.indexOf("data:") === 0) dataLine += l.slice(5).trim();
        });
        if (!dataLine) return;
        var evt;
        try { evt = JSON.parse(dataLine); } catch (e) { return; }
        if (evt.type === "meta" && evt.session_id) {
          currentSessionId = evt.session_id;
          updateSessionTitle(q);
        } else if (evt.type === "delta") {
          fullText += evt.content || "";
          mdEl.innerHTML = renderMarkdown(fullText);
          historyEl.scrollTop = historyEl.scrollHeight;
        } else if (evt.type === "error") {
          mdEl.innerHTML = '<span class="err-code">' + esc(evt.message || "服务异常") + "</span>";
          mdEl.parentElement.classList.add("error");
          fullText = "";
        } else if (evt.type === "done") {
          fullText = evt.content || fullText;
          mdEl.innerHTML = renderMarkdown(fullText);
        }
      }
      function finish() {
        streaming = false;
        sendBtn.disabled = false;
        if (!fullText) {
          mdEl.innerHTML = '<span class="err-code">未收到有效回复，请重试。</span>';
          mdEl.parentElement.classList.add("error");
        }
        loadSessions();
        ask.focus();
      }
      return pump();
    }).catch(function (err) {
      streaming = false;
      sendBtn.disabled = false;
      mdEl.innerHTML = '<span class="err-code">请求失败：' + esc(err.message || "无法连接后端") + "</span>";
      mdEl.parentElement.classList.add("error");
      ask.focus();
    });
  }

  function updateSessionTitle(firstMsg) {
    // 会话标题取首条消息前 16 字
    fetch(API + "api/sessions/" + currentSessionId + "/messages")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var msgs = data.messages || [];
        if (msgs.length === 1 && msgs[0].role === "user") {
          var title = msgs[0].content.slice(0, 16);
          fetch(API + "api/sessions/" + currentSessionId + "/rename", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: title })
          }).then(function () { return loadSessions(); });
        }
      });
  }

  /* ---------- 顶部导航面板 ---------- */
  var panels = {
    "智慧教育": ["围绕基础教育教师的真实教学任务，提供课堂设计、教研反思与智能支持。",
      ["开展教学设计", "如何开展课例研究", "数字素养提升建议", "AI课堂应用案例"]],
    "资源中心": ["这里提供学习资源、教学案例、政策解读等入口。也可以打开“优质资源推荐”页检索真实资源库。",
      ["推荐初中数学教学案例", "推荐数字素养学习资源", "如何检索教育研究文献", "生成教学资源筛选清单"]],
    "教师社区": ["交流备课经验、组织课例研讨与共建教学资源。社区发布及审核功能需要后续接入。",
      ["如何组织共同备课", "如何设计一次同课异构活动", "如何开展校本教研", "课例研究成果如何整理"]],
    "关于我们": ["ME-AITA 教师成长智能体：学用相生、研创贯通，面向师范生与中小学教师提供数字素养发展支持。",
      ["平台能做什么", "如何使用智能问答", "数字素养诊断说明", "教师成长如何评价"]],
    "教师入口": ["当前版本为本地单机运行，正式版将提供师范生、在职教师及教研指导人员的账号入口。",
      ["我是师范生，如何开始学习？", "我是中小学教师，如何开展数字素养提升？", "如何保存教学作品？", "如何查看成长档案？"]],
    "数字素养诊断": ["进入数字素养诊断页，完成基于《教师数字素养》标准的试用版测评。",
      ["打开数字素养诊断页"]],
    "优质资源推荐": ["进入优质资源推荐页，检索本地真实资源库（课程标准、数字素养材料、教学案例等）。",
      ["打开优质资源推荐页"]]
  };

  function openPanel(name) {
    var entry = panels[name] || panels["智慧教育"];
    dialogTitle.textContent = name;
    dialogDesc.textContent = entry[0];
    dialogTiles.replaceChildren();
    entry[1].forEach(function (label) {
      var b = document.createElement("button");
      b.textContent = label;
      b.addEventListener("click", function () {
        closeDialog();
        if (label === "打开数字素养诊断页") { location.href = "diagnosis.html"; return; }
        if (label === "打开优质资源推荐页") { location.href = "resources.html"; return; }
        ask.value = label;
        ask.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      dialogTiles.appendChild(b);
    });
    dialog.classList.add("open");
    $("#closeDialog").focus();
  }

  function closeDialog() { dialog.classList.remove("open"); }

  /* ---------- 事件绑定 ---------- */
  $("#closeDialog").addEventListener("click", closeDialog);
  dialog.addEventListener("click", function (e) { if (e.target === dialog) closeDialog(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDialog();
    if (e.key === "Enter" && e.target === ask && !e.shiftKey) {
      e.preventDefault();
      chatForm.requestSubmit();
    }
  });

  $$("[data-panel]").forEach(function (b) {
    b.addEventListener("click", function () { openPanel(b.dataset.panel); });
  });

  $$("[data-feature]").forEach(function (b) {
    b.addEventListener("click", function () {
      var f = b.dataset.feature;
      if (f === "智能问答") {
        ask.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else if (f === "数字素养诊断") {
        location.href = "diagnosis.html";
      } else if (f === "优质资源推荐") {
        location.href = "resources.html";
      } else {
        openPanel(f);
      }
    });
  });

  $$("[data-question]").forEach(function (b) {
    b.addEventListener("click", function () {
      ask.value = b.dataset.question;
      ask.focus();
    });
  });

  sessionSelect.addEventListener("change", function () {
    var id = parseInt(sessionSelect.value, 10);
    if (id) switchSession(id);
  });

  $("#newSessionBtn").addEventListener("click", function () {
    createSession("新会话").then(function () { clearChat(); ask.focus(); notify("已新建会话"); });
  });

  $("#delSessionBtn").addEventListener("click", deleteCurrentSession);

  searchToggle.addEventListener("click", function () {
    searchEnabled = !searchEnabled;
    searchToggle.setAttribute("aria-pressed", String(searchEnabled));
    searchToggle.style.background = searchEnabled ? "#e9f3ff" : "";
    notify(searchEnabled ? "已开启联网搜索（模型将检索网络信息）" : "已关闭联网搜索");
  });

  $("#modelToggle").addEventListener("click", function () {
    notify("当前模型：" + modelName.textContent + "（可在项目根目录 .env 的 ZHIPU_MODEL 中切换）");
  });

  /* ---------- 会话菜单（右上角收起式） ---------- */
  var sessionBtn = document.getElementById("sessionBtn");
  var sessionMenu = document.getElementById("sessionMenu");
  function toggleSessionMenu(force) {
    if (!sessionBtn || !sessionMenu) return;
    var open = typeof force === "boolean" ? force : sessionMenu.hidden;
    sessionMenu.hidden = !open;
    sessionBtn.setAttribute("aria-expanded", String(open));
  }
  if (sessionBtn && sessionMenu) {
    sessionBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleSessionMenu();
    });
    sessionMenu.addEventListener("click", function (e) { e.stopPropagation(); });
    document.addEventListener("click", function (e) {
      if (sessionMenu.hidden) return;
      if (sessionMenu.contains(e.target) || sessionBtn.contains(e.target)) return;
      toggleSessionMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") toggleSessionMenu(false);
    });
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    sendMessage();
  });

  /* ---------- 初始化 ---------- */
  function init() {
    fetch(API + "api/info").then(function (r) { return r.json(); }).then(function (info) {
      modelName.textContent = info.model || "已连接";
      if (!info.api_configured) notify("后端未配置 API Key，请检查 .env");
    }).catch(function () {
      modelName.textContent = "未连接";
      notify("后端服务未启动：请运行项目根目录的 启动智能体.bat");
    });
    loadSessions().then(function (created) {
      if (created) { /* 已自动新建 */ }
    });
  }

  init();
})();

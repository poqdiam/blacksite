/* ── AdminChat — Phase 23 ───────────────────────────────────────────────────── */
/* jshint esversion: 11 */
"use strict";

const AdminChat = (() => {
  let ws = null;
  let reconnectDelay = 1000;
  let reconnectTimer = null;
  const MAX_DELAY      = 30000;
  const MAX_WINDOWS    = 3;
  let SIDEBAR_VISIBLE  = 5;    // overridden by server setting via init()
  let SHOW_AWAY_MSG    = true; // overridden by server setting via init()

  const openWindows = {};   // room → { el, typingTimer, lastMsgId }
  const presence    = {};   // username → {status, away_msg}
  let allUsers      = [];   // all configured admin users (from /api/admin-chat/users)
  let myUsername    = "";
  let myStatus      = "online";
  let notifPermission = false;

  const DEFAULT_COLORS = {
    myBubble:    "#002918",
    myText:      "#00ffcc",
    theirBubble: "#141425",
    chatBg:      "#0f0f1a"
  };

  // ── Dimension persistence — sessionStorage only (H6: does not survive logout) ──

  function _savedDim(room) {
    // Per spec (H6): chat dimensions reset each session, not restored from previous login
    return null;
  }
  function _saveDim(room, w, h) {
    // No-op: dimensions are not persisted per H6 spec (use hardcoded defaults each session)
  }

  // ── Recent contacts ───────────────────────────────────────────────────────────

  function _touchRecent(username) {
    let recent = [];
    try { recent = JSON.parse(localStorage.getItem("bsv-chat-recent") || "[]"); } catch {}
    recent = recent.filter(r => r.u !== username);
    recent.unshift({u: username, ts: Date.now()});
    localStorage.setItem("bsv-chat-recent", JSON.stringify(recent.slice(0, 20)));
  }

  function _getRecentMap() {
    try {
      const arr = JSON.parse(localStorage.getItem("bsv-chat-recent") || "[]");
      const m = {};
      arr.forEach((r, i) => { m[r.u] = i; });
      return m;
    } catch { return {}; }
  }

  // ── Color preferences ─────────────────────────────────────────────────────────

  function _getColors(room) {
    try {
      return JSON.parse(localStorage.getItem("bsv-chat-colors-" + room) || "null") || {...DEFAULT_COLORS};
    } catch { return {...DEFAULT_COLORS}; }
  }

  function _applyColors(win, room) {
    const c = _getColors(room);
    win.style.setProperty("--chat-own",      c.myBubble);
    win.style.setProperty("--chat-own-text", c.myText);
    win.style.setProperty("--chat-other",    c.theirBubble);
    win.style.setProperty("--chat-bg",       c.chatBg);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function _dmRoom(other) {
    return [myUsername, other].sort().join(":");
  }

  function _roomTitle(room) {
    if (room === "@group") return "# group";
    const parts = room.split(":");
    return "@ " + parts.find(u => u !== myUsername);
  }

  function _fmtTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
    } catch { return ""; }
  }

  function _connDot(state) {
    const dot = document.getElementById("sbChatConnDot");
    if (!dot) return;
    dot.style.background =
      state === "open"  ? "var(--chat-online)" :
      state === "error" ? "var(--red)"         : "#555";
    dot.title = state;
  }

  // ── Notifications ─────────────────────────────────────────────────────────────

  function _requestNotifPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") { notifPermission = true; return; }
    if (Notification.permission !== "denied") {
      Notification.requestPermission().then(p => { notifPermission = p === "granted"; });
    }
  }

  function _notify(title, body) {
    if (myStatus === "away") return;
    if (!notifPermission || document.hasFocus()) return;
    try {
      new Notification(title, {body, icon: "/static/favicon.ico", tag: "adminchat"});
    } catch {}
  }

  // ── Sidebar rendering ─────────────────────────────────────────────────────────

  function _makeUserRow(u) {
    const row = document.createElement("div");
    row.className = "sb-chat-user";
    row.dataset.username = u.username;

    const dot = document.createElement("span");
    dot.className = `status-dot status-${u.status || "offline"}`;
    dot.title = u.away_msg ? `Away: ${u.away_msg}` : (u.status || "offline");

    // Name + optional away message
    const nameWrap = document.createElement("div");
    nameWrap.style.flex = "1";
    nameWrap.style.minWidth = "0";
    const name = document.createElement("div");
    name.textContent = u.display_name || u.username;
    name.style.overflow = "hidden";
    name.style.textOverflow = "ellipsis";
    name.style.whiteSpace = "nowrap";
    nameWrap.appendChild(name);
    if (SHOW_AWAY_MSG && u.away_msg && u.status === "away") {
      const away = document.createElement("div");
      away.textContent = u.away_msg;
      away.style.cssText = "font-size:0.7em;color:var(--chat-away,#f44336);opacity:0.8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
      nameWrap.appendChild(away);
    }

    const badge = document.createElement("span");
    badge.className = "unread-dot";
    badge.id = `unread-${_dmRoom(u.username)}`;
    badge.style.display = "none";

    row.append(dot, nameWrap, badge);
    row.addEventListener("click", () => openRoom(
      _dmRoom(u.username), "@ " + (u.display_name || u.username)
    ));
    return row;
  }

  function renderSidebar() {
    const container = document.getElementById("sbChatUsers");
    if (!container) return;
    container.innerHTML = "";

    const recentMap = _getRecentMap();

    // Merge allUsers with live presence data
    const users = allUsers
      .filter(u => u.username !== myUsername)
      .map(u => ({
        username:     u.username,
        display_name: u.display_name || u.username,
        status:       (presence[u.username] || {}).status   || "offline",
        away_msg:     (presence[u.username] || {}).away_msg || ""
      }));

    // Sort: recently contacted first, then alphabetical
    users.sort((a, b) => {
      const ra = recentMap.hasOwnProperty(a.username) ? recentMap[a.username] : 9999;
      const rb = recentMap.hasOwnProperty(b.username) ? recentMap[b.username] : 9999;
      if (ra !== rb) return ra - rb;
      return a.username.localeCompare(b.username);
    });

    const visible = users.slice(0, SIDEBAR_VISIBLE);
    const rest    = users.slice(SIDEBAR_VISIBLE);

    visible.forEach(u => container.appendChild(_makeUserRow(u)));

    if (rest.length > 0) {
      const moreList = document.createElement("div");
      moreList.style.display = "none";
      rest.forEach(u => moreList.appendChild(_makeUserRow(u)));

      let expanded = false;
      const moreBtn = document.createElement("div");
      moreBtn.className = "sb-chat-more";
      moreBtn.textContent = `More (${rest.length})`;
      moreBtn.addEventListener("click", () => {
        expanded = !expanded;
        moreList.style.display = expanded ? "" : "none";
        moreBtn.textContent = expanded ? "Less ▲" : `More (${rest.length})`;
      });

      container.appendChild(moreBtn);
      container.appendChild(moreList);
    }

    // Update status dots in open DM windows
    Object.keys(openWindows).forEach(room => {
      if (room === "@group") return;
      const other = room.split(":").find(u => u !== myUsername);
      const p2 = presence[other];
      if (!p2) return;
      const win = openWindows[room];
      if (!win) return;
      const dot = win.el.querySelector(".chat-status-dot");
      if (dot) {
        dot.className = `status-dot chat-status-dot status-${p2.status}`;
        dot.title = p2.away_msg ? `Away: ${p2.away_msg}` : p2.status;
      }
    });
  }

  async function fetchAllUsers() {
    try {
      const res = await fetch("/api/admin-chat/users");
      if (!res.ok) return;
      allUsers = await res.json();
      allUsers.forEach(u => {
        if (u.username !== myUsername) {
          presence[u.username] = {status: u.status || "offline", away_msg: u.away_msg || ""};
        }
      });
      renderSidebar();
    } catch {}
  }

  // ── Unread badges ─────────────────────────────────────────────────────────────

  function _setUnread(room, count) {
    const badge = document.getElementById(`unread-${room}`);
    if (badge) {
      if (count > 0) { badge.textContent = count; badge.style.display = "inline-flex"; }
      else { badge.style.display = "none"; }
    }
    const win = openWindows[room];
    if (win) {
      const hdrBadge = win.el.querySelector(".chat-unread-hdr");
      if (hdrBadge) {
        if (count > 0) { hdrBadge.textContent = count; hdrBadge.style.display = "inline-flex"; }
        else { hdrBadge.style.display = "none"; }
      }
    }
  }

  function _applyUnreadCounts(counts) {
    Object.entries(counts).forEach(([room, cnt]) => _setUnread(room, cnt));
  }

  // ── Window management ─────────────────────────────────────────────────────────

  function openRoom(room, title) {
    if (openWindows[room]) {
      const win = openWindows[room];
      if (win.el.classList.contains("minimized")) win.el.classList.remove("minimized");
      win.el.querySelector("textarea")?.focus();
      return;
    }

    // Enforce max open windows
    const rooms = Object.keys(openWindows);
    if (rooms.length >= MAX_WINDOWS) closeWindow(rooms[0]);

    const container = document.getElementById("chatWindowContainer");
    if (!container) return;

    const win = document.createElement("div");
    win.className = "chat-window";
    win.dataset.room = room;

    const other   = room !== "@group" ? room.split(":").find(u => u !== myUsername) : null;
    const presData = other ? (presence[other] || {status: "offline", away_msg: ""}) : null;

    win.innerHTML = `
      <div class="chat-header">
        ${presData
          ? `<span class="status-dot chat-status-dot status-${presData.status}"
                  title="${presData.away_msg ? "Away: " + presData.away_msg : presData.status}"></span>`
          : ""}
        <span class="chat-title">${title}</span>
        <span class="chat-unread-hdr" style="display:none"></span>
        <button class="chat-gear"   title="Color settings">⚙</button>
        <button class="chat-popout" title="Pop out">⊞</button>
        <button class="chat-close"  title="Close">✕</button>
      </div>
      <div class="chat-color-panel">
        <label>My bubble    <input type="color" data-pref="myBubble"></label>
        <label>My text      <input type="color" data-pref="myText"></label>
        <label>Their bubble <input type="color" data-pref="theirBubble"></label>
        <label>Background   <input type="color" data-pref="chatBg"></label>
      </div>
      <div class="chat-body"></div>
      <div class="chat-typing"></div>
      <div class="chat-input-row">
        <textarea rows="1" placeholder="Message…"></textarea>
        <button class="chat-send" title="Send">➤</button>
      </div>`;

    // Apply saved colors
    _applyColors(win, room);

    // Initialize color pickers
    const gearBtn    = win.querySelector(".chat-gear");
    const colorPanel = win.querySelector(".chat-color-panel");
    const colors     = _getColors(room);
    colorPanel.querySelectorAll("input[data-pref]").forEach(input => {
      input.value = colors[input.dataset.pref] || DEFAULT_COLORS[input.dataset.pref] || "#000000";
      input.addEventListener("input", () => {
        const current = _getColors(room);
        current[input.dataset.pref] = input.value;
        localStorage.setItem("bsv-chat-colors-" + room, JSON.stringify(current));
        _applyColors(win, room);
      });
    });
    gearBtn.addEventListener("click", e => {
      e.stopPropagation();
      const isOpen = colorPanel.style.display === "grid";
      colorPanel.style.display = isOpen ? "none" : "grid";
    });

    // Pop-out
    win.querySelector(".chat-popout").addEventListener("click", e => {
      e.stopPropagation();
      window.open(
        "/chat/popup/" + encodeURIComponent(room),
        "bsv-chat-" + room,
        "width=380,height=560,resizable=yes,menubar=no,toolbar=no,location=no,status=no"
      );
      closeWindow(room);
    });

    // Minimize on header click (not on action buttons)
    win.querySelector(".chat-header").addEventListener("click", e => {
      if (e.target.closest(".chat-close, .chat-gear, .chat-popout")) return;
      win.classList.toggle("minimized");
    });
    win.querySelector(".chat-close").addEventListener("click", e => {
      e.stopPropagation();
      closeWindow(room);
    });

    // Send on click or Enter (Shift+Enter = newline)
    const textarea = win.querySelector("textarea");
    const doSend = () => {
      const body = textarea.value.trim();
      if (!body) return;
      sendMessage(room, body);
      textarea.value = "";
      textarea.style.height = "auto";
    };
    win.querySelector(".chat-send").addEventListener("click", doSend);
    textarea.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSend(); }
    });

    // Auto-resize textarea
    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 80) + "px";
    });

    // Typing indicator broadcast
    let typingTimer = null;
    textarea.addEventListener("input", () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: "typing", room}));
      }
      clearTimeout(typingTimer);
      typingTimer = setTimeout(() => {}, 3000);
    });

    // Restore saved dimensions
    const savedDim = _savedDim(room);
    if (savedDim) {
      win.style.width  = Math.max(200, Math.min(600, savedDim.w)) + "px";
      win.style.height = Math.max(36,  Math.min(700, savedDim.h)) + "px";
    }

    // Resize handles
    const resizeTop  = document.createElement("div");
    resizeTop.className = "chat-resize-handle";
    const resizeLeft = document.createElement("div");
    resizeLeft.className = "chat-resize-handle-left";
    win.prepend(resizeLeft);
    win.prepend(resizeTop);

    function _startResize(e, axis) {
      e.preventDefault();
      const startX = e.clientX, startY = e.clientY;
      const startW = win.offsetWidth,  startH = win.offsetHeight;
      const onMove = e => {
        if (axis !== "h") win.style.width  = Math.max(200, Math.min(600, startW - (e.clientX - startX))) + "px";
        if (axis !== "w") win.style.height = Math.max(200, Math.min(700, startH - (e.clientY - startY))) + "px";
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup",   onUp);
        _saveDim(room, win.offsetWidth, win.offsetHeight);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup",   onUp);
    }
    resizeTop.addEventListener("mousedown",  e => _startResize(e, "h"));
    resizeLeft.addEventListener("mousedown", e => _startResize(e, "w"));

    container.appendChild(win);
    openWindows[room] = {el: win, typingTimer: null, lastMsgId: 0};

    // Mark read on focus
    textarea.addEventListener("focus", () => {
      const state = openWindows[room];
      if (state && state.lastMsgId) {
        markRead(room, state.lastMsgId);
        _setUnread(room, 0);
      }
    });

    loadHistory(room, win);
    textarea.focus();
  }

  function closeWindow(room) {
    const win = openWindows[room];
    if (!win) return;
    win.el.remove();
    delete openWindows[room];
  }

  // ── History ───────────────────────────────────────────────────────────────────

  async function loadHistory(room, winEl) {
    try {
      const res = await fetch(`/api/admin-chat/history/${encodeURIComponent(room)}`);
      if (!res.ok) return;
      const msgs = await res.json();
      const body = winEl.querySelector(".chat-body");
      if (!body) return;
      msgs.forEach(m => _renderMessage(body, m));
      body.scrollTop = body.scrollHeight;
      if (msgs.length) {
        const state = openWindows[room];
        if (state) {
          state.lastMsgId = msgs[msgs.length - 1].id;
          markRead(room, state.lastMsgId);
          _setUnread(room, 0);
        }
      }
    } catch {}
  }

  // ── Messages ──────────────────────────────────────────────────────────────────

  function _renderMessage(bodyEl, msg) {
    const isOwn = msg.from_user === myUsername;
    const wrap  = document.createElement("div");
    wrap.className = `msg-wrap ${isOwn ? "own" : "other"}`;
    if (!isOwn) {
      const sender = document.createElement("div");
      sender.className = "msg-sender";
      sender.textContent = msg.from_user;
      wrap.appendChild(sender);
    }
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = msg.body;
    const time = document.createElement("div");
    time.className = "msg-time";
    time.textContent = _fmtTime(msg.sent_at);
    wrap.append(bubble, time);
    bodyEl.appendChild(wrap);
  }

  function appendMessage(room, msg) {
    const state = openWindows[room];
    if (!state) return;
    const body = state.el.querySelector(".chat-body");
    if (!body) return;
    const isAtBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 60;
    _renderMessage(body, msg);
    if (isAtBottom) body.scrollTop = body.scrollHeight;
    state.lastMsgId = Math.max(state.lastMsgId, msg.id);

    if (document.hasFocus() && !state.el.classList.contains("minimized")) {
      markRead(room, msg.id);
    } else {
      const badge = document.getElementById(`unread-${room}`);
      const cur = badge ? (parseInt(badge.textContent, 10) || 0) : 0;
      _setUnread(room, cur + 1);
      _notify(_roomTitle(room), `${msg.from_user}: ${msg.body}`);
    }
  }

  function sendMessage(room, body) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({type: "message", room, body}));
    // Track recency for DM contacts
    if (room !== "@group") {
      const other = room.split(":").find(u => u !== myUsername);
      if (other) { _touchRecent(other); renderSidebar(); }
    }
  }

  function markRead(room, lastId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({type: "read", room, last_id: lastId}));
  }

  // ── Status ────────────────────────────────────────────────────────────────────

  function setMyStatus(status, msg) {
    myStatus = status;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({type: "status", status, away_msg: msg || ""}));
    const myDot = document.getElementById("myStatusDot");
    if (myDot) myDot.className = `status-dot status-${status}`;
  }

  // ── WebSocket lifecycle ───────────────────────────────────────────────────────

  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws/admin-chat`);
    _connDot("connecting");
    ws.addEventListener("open",    onOpen);
    ws.addEventListener("message", onMessage);
    ws.addEventListener("close",   onClose);
    ws.addEventListener("error",   () => _connDot("error"));
  }

  function onOpen() {
    reconnectDelay = 1000;
    clearTimeout(reconnectTimer);
    _connDot("open");
    _requestNotifPermission();
  }

  function onMessage(evt) {
    let data;
    try { data = JSON.parse(evt.data); } catch { return; }

    if (data.type === "presence") {
      // Update live presence; mark anyone NOT in the list as offline
      const liveSet = new Set();
      data.users.forEach(u => {
        presence[u.username] = {status: u.status, away_msg: u.away_msg || ""};
        liveSet.add(u.username);
      });
      allUsers.forEach(u => {
        if (!liveSet.has(u.username)) {
          presence[u.username] = {status: "offline", away_msg: ""};
        }
      });
      renderSidebar();

    } else if (data.type === "unread") {
      _applyUnreadCounts(data.counts);

    } else if (data.type === "message") {
      const room = data.room;
      if (room !== "@group" && myUsername && room.includes(myUsername)) {
        const other = room.split(":").find(u => u !== myUsername);
        if (other) { _touchRecent(other); renderSidebar(); }
        if (!openWindows[room]) openRoom(room, "@ " + other);
      }
      if (openWindows[room]) {
        appendMessage(room, data);
      } else {
        const badge = document.getElementById(`unread-${room}`);
        const cur = badge ? (parseInt(badge.textContent, 10) || 0) : 0;
        _setUnread(room, cur + 1);
        _notify(_roomTitle(room), `${data.from_user}: ${data.body}`);
      }

    } else if (data.type === "typing") {
      const state = openWindows[data.room];
      if (!state) return;
      const typingEl = state.el.querySelector(".chat-typing");
      if (!typingEl) return;
      typingEl.textContent = `${data.from_user} is typing…`;
      clearTimeout(state.typingTimer);
      state.typingTimer = setTimeout(() => { typingEl.textContent = ""; }, 3000);
    }
  }

  function onClose(evt) {
    _connDot("closed");
    if (evt.code === 4003) return;
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_DELAY);
      connect();
    }, reconnectDelay);
  }

  // ── Sidebar wiring ────────────────────────────────────────────────────────────

  function _wireSidebar() {
    const groupBtn = document.getElementById("sbGroupChatBtn");
    if (groupBtn) groupBtn.addEventListener("click", () => openRoom("@group", "# group"));

    const statusToggle = document.getElementById("sbStatusToggle");
    const awayMsgRow   = document.getElementById("sbAwayMsgRow");
    const awayMsgInput = document.getElementById("sbAwayMsg");

    if (statusToggle) {
      statusToggle.addEventListener("change", () => {
        const st = statusToggle.value;
        if (awayMsgRow) awayMsgRow.style.display = st === "away" ? "" : "none";
        setMyStatus(st, st === "away" && awayMsgInput ? awayMsgInput.value : "");
      });
    }
    if (awayMsgInput) {
      let awayInputTimer = null;
      awayMsgInput.addEventListener("input", () => {
        clearTimeout(awayInputTimer);
        awayInputTimer = setTimeout(() => setMyStatus("away", awayMsgInput.value), 500);
      });
    }
  }

  // ── Public init ───────────────────────────────────────────────────────────────

  function init(username, opts) {
    myUsername = username || "";
    if (opts) {
      if (typeof opts.visibleCount === "number") SIDEBAR_VISIBLE = Math.max(1, opts.visibleCount);
      if (typeof opts.showAwayMsg  === "boolean") SHOW_AWAY_MSG  = opts.showAwayMsg;
    }
    // Also check per-user localStorage override
    const localCount = parseInt(localStorage.getItem("bsv-chat-visible-count") || "");
    if (!isNaN(localCount) && localCount > 0) SIDEBAR_VISIBLE = localCount;
    const localAway = localStorage.getItem("bsv-chat-show-away");
    if (localAway !== null) SHOW_AWAY_MSG = localAway !== "false";

    _wireSidebar();
    fetchAllUsers();   // load all admin users (offline + online) into sidebar
    connect();         // connect WS (will push live presence updates)
  }

  return { init };
})();

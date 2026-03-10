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
  const poppedOut   = {};   // room → popup window ref (tracks rooms open in popup windows)
  const presence    = {};   // username → {status, away_msg}
  let allUsers      = [];   // all configured admin users (from /api/admin-chat/users)
  let myUsername    = "";
  let myStatus      = "online";
  let notifPermission = false;

  // ── Chat window persistence ───────────────────────────────────────────────────
  const SS_OPEN_ROOMS = "bsv-chat-open-rooms";

  function _saveOpenRooms() {
    const state = {};
    Object.keys(openWindows).forEach(room => {
      state[room] = openWindows[room].el.classList.contains("minimized") ? "minimized" : "open";
    });
    sessionStorage.setItem(SS_OPEN_ROOMS, JSON.stringify(state));
  }

  function _restoreOpenRooms() {
    let state;
    try { state = JSON.parse(sessionStorage.getItem(SS_OPEN_ROOMS) || "{}"); } catch { return; }
    Object.entries(state).forEach(([room, vis]) => {
      if (!openWindows[room]) openRoom(room, _roomTitle(room));
      if (vis === "minimized" && openWindows[room]) {
        openWindows[room].el.classList.add("minimized");
      }
    });
  }

  // ── Sound alerts ─────────────────────────────────────────────────────────────
  const LS_SOUND  = "bsv-chat-sound";   // "on" | "off-session" | "off"
  let _soundMutedSession = false;        // true = muted until page close
  let _audioCtx = null;

  function _getSoundPref() {
    return localStorage.getItem(LS_SOUND) || "on";
  }

  function _soundEnabled() {
    if (_soundMutedSession) return false;
    return _getSoundPref() !== "off";
  }

  function _ding() {
    if (!_soundEnabled()) return;
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = _audioCtx;
      const now = ctx.currentTime;
      // Two-tone soft chime: 880 Hz then 1108 Hz
      [[880, now, 0.12], [1108, now + 0.11, 0.09]].forEach(([freq, start, peak]) => {
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(peak, start + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.45);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + 0.46);
      });
    } catch {}
  }

  // ── Sound context menu ───────────────────────────────────────────────────────
  let _soundCtxMenu = null;

  function _removeSoundCtxMenu() {
    if (_soundCtxMenu) { _soundCtxMenu.remove(); _soundCtxMenu = null; }
  }

  function _showSoundCtxMenu(x, y) {
    _removeSoundCtxMenu();
    const pref  = _getSoundPref();
    const muted = !_soundEnabled();

    const menu = document.createElement("div");
    menu.id = "chat-sound-ctx";
    menu.style.cssText = `position:fixed;z-index:99999;background:var(--card,#1a1a2e);
      border:1px solid rgba(0,255,204,0.2);border-radius:6px;padding:4px 0;
      box-shadow:0 6px 24px rgba(0,0,0,0.6);font-size:0.82em;min-width:210px;
      user-select:none;`;
    menu.style.left = Math.min(x, window.innerWidth  - 220) + "px";
    menu.style.top  = Math.min(y, window.innerHeight - 130) + "px";

    const label = document.createElement("div");
    label.textContent = "🔔 Chat Sound Alerts";
    label.style.cssText = "padding:6px 14px 4px;font-size:0.72em;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:rgba(0,255,204,0.5);cursor:default;";
    menu.appendChild(label);

    const sep = () => { const d = document.createElement("div"); d.style.cssText="height:1px;background:rgba(255,255,255,0.07);margin:4px 0;"; return d; };

    const item = (icon, text, active, fn) => {
      const el = document.createElement("div");
      el.style.cssText = `padding:8px 14px;cursor:pointer;display:flex;align-items:center;gap:8px;
        color:${active ? "var(--cyan,#00ffcc)" : "var(--text,#e0e0e0)"};
        font-weight:${active ? "700" : "400"};`;
      el.innerHTML = `<span style="font-size:1.1em">${icon}</span>${text}${active ? ' <span style="margin-left:auto;font-size:0.75em;opacity:.6">✓</span>' : ""}`;
      el.addEventListener("mouseenter", () => el.style.background = "rgba(0,255,204,0.07)");
      el.addEventListener("mouseleave", () => el.style.background = "");
      el.addEventListener("click", () => { _removeSoundCtxMenu(); fn(); });
      return el;
    };

    menu.appendChild(item("🔔", "Alerts on",            pref === "on" && !_soundMutedSession, () => {
      _soundMutedSession = false;
      localStorage.setItem(LS_SOUND, "on");
    }));
    menu.appendChild(item("🔕", "Mute this session",    _soundMutedSession,                  () => {
      _soundMutedSession = true;
      localStorage.setItem(LS_SOUND, "on"); // restore perm after session ends
    }));
    menu.appendChild(sep());
    menu.appendChild(item("🚫", "Mute permanently",     pref === "off" && !_soundMutedSession, () => {
      _soundMutedSession = false;
      localStorage.setItem(LS_SOUND, "off");
    }));

    document.body.appendChild(menu);
    _soundCtxMenu = menu;

    // Dismiss on next click / Escape
    setTimeout(() => {
      document.addEventListener("click", _removeSoundCtxMenu, { once: true, capture: true });
      document.addEventListener("keydown", function esc(e) {
        if (e.key === "Escape") { _removeSoundCtxMenu(); document.removeEventListener("keydown", esc); }
      });
    }, 0);
  }

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

  function _makeSectionHdr(label) {
    const h = document.createElement("div");
    h.className = "sb-section-hdr";
    h.textContent = label;
    return h;
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

    const statusRank = {online: 0, away: 1, offline: 2};

    // Recent: up to 5 admins with actual DM history, sorted by most recent
    const recentUsers = users
      .filter(u => recentMap.hasOwnProperty(u.username))
      .sort((a, b) => recentMap[a.username] - recentMap[b.username])
      .slice(0, 5);
    const recentSet = new Set(recentUsers.map(u => u.username));

    // All admins: everyone else, sorted online > away > offline > alpha
    const otherUsers = users
      .filter(u => !recentSet.has(u.username))
      .sort((a, b) => {
        const sa = statusRank[a.status] ?? 2;
        const sb = statusRank[b.status] ?? 2;
        if (sa !== sb) return sa - sb;
        return a.username.localeCompare(b.username);
      });

    // Render Recent section
    if (recentUsers.length > 0) {
      container.appendChild(_makeSectionHdr("Recent"));
      recentUsers.forEach(u => container.appendChild(_makeUserRow(u)));
    }

    // Render All Admins section
    if (otherUsers.length > 0) {
      container.appendChild(_makeSectionHdr("All Admins"));
      otherUsers.forEach(u => container.appendChild(_makeUserRow(u)));
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
        <label class="chat-img-btn" title="Send image" aria-label="Attach image">
          📎<input type="file" accept="image/*" class="chat-img-input" style="display:none">
        </label>
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
      const popup = window.open(
        "/chat/popup?room=" + encodeURIComponent(room),
        "bsv-chat-" + room,
        "width=380,height=560,resizable=yes,menubar=no,toolbar=no,location=no,status=no"
      );
      if (popup) {
        poppedOut[room] = popup;
        const poll = setInterval(() => {
          if (!poppedOut[room] || poppedOut[room].closed) {
            delete poppedOut[room];
            clearInterval(poll);
          }
        }, 1000);
      }
      closeWindow(room);
    });

    // Minimize on header click (not on action buttons)
    win.querySelector(".chat-header").addEventListener("click", e => {
      if (e.target.closest(".chat-close, .chat-gear, .chat-popout")) return;
      win.classList.toggle("minimized");
      _saveOpenRooms();
    });
    // Right-click on header → sound alert menu
    win.querySelector(".chat-header").addEventListener("contextmenu", e => {
      e.preventDefault();
      _showSoundCtxMenu(e.clientX, e.clientY);
    });
    win.querySelector(".chat-close").addEventListener("click", e => {
      e.stopPropagation();
      if (win.classList.contains("minimized")) {
        closeWindow(room);   // already minimized → fully remove
      } else {
        win.classList.add("minimized");   // expanded → just minimize
      }
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

    // Image upload
    const imgInput = win.querySelector(".chat-img-input");
    imgInput.addEventListener("change", async () => {
      const file = imgInput.files[0];
      imgInput.value = "";
      if (!file) return;
      if (!file.type.startsWith("image/")) { alert("Please select an image file."); return; }
      if (file.size > 8 * 1024 * 1024) { alert("Image must be under 8 MB."); return; }
      await _uploadAndSendImage(room, file);
    });

    // Paste screenshot / clipboard image
    textarea.addEventListener("paste", async (e) => {
      const items = Array.from(e.clipboardData?.items || []);
      const imgItem = items.find(it => it.kind === "file" && it.type.startsWith("image/"));
      if (!imgItem) return;           // let normal text paste through
      e.preventDefault();
      const file = imgItem.getAsFile();
      if (!file) return;
      if (file.size > 8 * 1024 * 1024) { alert("Image must be under 8 MB."); return; }
      await _uploadAndSendImage(room, file);
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
    _saveOpenRooms();

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
    _saveOpenRooms();
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
    if (msg.media_url) {
      const img = document.createElement("img");
      img.src = msg.media_url;
      img.className = "chat-img-preview";
      img.alt = msg.body || "image";
      img.loading = "lazy";
      img.addEventListener("click", () => window.open(msg.media_url, "_blank"));
      bubble.appendChild(img);
      if (msg.body) {
        const cap = document.createElement("div");
        cap.className = "chat-img-caption";
        cap.textContent = msg.body;
        bubble.appendChild(cap);
      }
    } else {
      bubble.textContent = msg.body;
    }
    const time = document.createElement("div");
    time.className = "msg-time";
    time.textContent = _fmtTime(msg.sent_at);
    wrap.append(bubble, time);
    bodyEl.appendChild(wrap);
  }

  async function _uploadAndSendImage(room, file) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const resp = await fetch("/api/admin-chat/upload", {method: "POST", body: fd});
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert("Upload failed: " + (err.detail || resp.status));
        return;
      }
      const {url, mime} = await resp.json();
      ws.send(JSON.stringify({type: "image", room, url, mime, caption: ""}));
      if (room !== "@group") {
        const other = room.split(":").find(u => u !== myUsername);
        if (other) { _touchRecent(other); renderSidebar(); }
      }
    } catch (e) {
      alert("Upload error: " + e.message);
    }
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
      _notify(_roomTitle(room), `${msg.from_user}: ${msg.media_url ? "📎 Image" : msg.body}`);
      _ding();
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
    const navDot = document.getElementById("navStatusDot");
    if (navDot) navDot.style.background = status === "away" ? "var(--red)" : "var(--green)";
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
    _restoreOpenRooms();
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

    } else if (data.type === "message" || data.type === "image") {
      const room = data.room;
      if (room !== "@group" && myUsername && room.includes(myUsername)) {
        const other = room.split(":").find(u => u !== myUsername);
        if (other) { _touchRecent(other); renderSidebar(); }
        if (!openWindows[room] && !poppedOut[room]) openRoom(room, "@ " + other);
      }
      if (openWindows[room]) {
        appendMessage(room, data);
      } else {
        const badge = document.getElementById(`unread-${room}`);
        const cur = badge ? (parseInt(badge.textContent, 10) || 0) : 0;
        _setUnread(room, cur + 1);
        _notify(_roomTitle(room), `${data.from_user}: ${data.media_url ? "📎 Image" : data.body}`);
        _ding();
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

    // Footer name: left-click toggles online/away; right-click opens away-message context menu
    const nameEl = document.getElementById("sb-name-status");
    const awayCtx = document.getElementById("sb-away-ctx");

    if (nameEl) {
      nameEl.addEventListener("click", () => {
        const newSt = myStatus === "online" ? "away" : "online";
        setMyStatus(newSt, "");
        nameEl.title = newSt === "online"
          ? "Online — Click to toggle Away · Right-click for away message"
          : "Away — Click to go Online · Right-click to set away message";
      });

      // contextmenu on sb-name-status is handled by sbOpenNameCtx() in base.html
    }
  }

  // ── Public init ───────────────────────────────────────────────────────────────

  function updateMyName(newName) {
    // Called by base.html after a successful chat name save
    const el = document.getElementById("sbMyDisplayName");
    if (el && newName) el.textContent = newName;
  }

  function init(username, opts) {
    myUsername = username || "";
    if (opts) {
      if (typeof opts.visibleCount === "number") SIDEBAR_VISIBLE = Math.max(1, opts.visibleCount);
      if (typeof opts.showAwayMsg  === "boolean") SHOW_AWAY_MSG  = opts.showAwayMsg;
      // chatName is used by base.html; nothing extra needed here
    }
    // Also check per-user localStorage override
    const localCount = parseInt(localStorage.getItem("bsv-chat-visible-count") || "");
    if (!isNaN(localCount) && localCount > 0) SIDEBAR_VISIBLE = localCount;
    const localAway = localStorage.getItem("bsv-chat-show-away");
    if (localAway !== null) SHOW_AWAY_MSG = localAway !== "false";

    _wireSidebar();
    fetchAllUsers();   // load all admin users (offline + online) into sidebar
    connect();         // connect WS (will push live presence updates)

    // ── Central attach function — always looks up container fresh ───────────────
    function _reattachWindows() {
      const c = document.getElementById("chatWindowContainer");
      if (!c) return;
      let attached = 0;
      Object.keys(openWindows).forEach(room => {
        const win = openWindows[room];
        if (win && !c.contains(win.el)) { c.appendChild(win.el); attached++; }
      });
      // If nothing was in the registry, try sessionStorage (handles full reloads)
      if (Object.keys(openWindows).length === 0) _restoreOpenRooms();
    }

    // Watch the container for window removal (uses fresh getElementById each callback)
    const _containerObs = new MutationObserver(() => _reattachWindows());
    const _startContainerObs = () => {
      const c = document.getElementById("chatWindowContainer");
      if (c) _containerObs.observe(c, {childList: true});
    };
    _startContainerObs();

    // Watch body: if the container element itself is replaced/re-added, restart observer
    new MutationObserver(() => {
      _containerObs.disconnect();
      _startContainerObs();
      _reattachWindows();
    }).observe(document.body, {childList: true, subtree: false});

    // Re-attach after htmx navigations and history restores
    document.addEventListener("htmx:afterSettle",    _reattachWindows);
    document.addEventListener("htmx:historyRestore", () => setTimeout(_reattachWindows, 50));
  }

  return { init, setMyStatus, updateMyName };
})();

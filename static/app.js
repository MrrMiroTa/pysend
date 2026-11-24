(() => {
  const $ = (s) => document.querySelector(s);
  const csrf = $('meta[name=csrf]').content;
  const SVGNS = "http://www.w3.org/2000/svg";
  const DEFAULT_TPL = `សួស្តីបង! គណនី GPS របស់បង ({count} គ្រឿង) នឹងផុតកំណត់នៅថ្ងៃទី {expiry_date}\n\nសូមបងទំនាក់ទំនងបន្តសេវាតាមរយៈលេខទំនាក់ទំនង {phone} (Call / Telegram)។\n\nសូមបងទំនាក់ទំនងបន្តសេវាអោយបានមុនថ្ងៃផុតកំណត់ ជៀសវាងការផ្អាកការប្រើប្រាស់បណ្ដោះអាសន្ន និងការបន្តសេវាមិនបានជោគជ័យដោយសារក្រុមហ៊ុនស៊ីមកាតមិនបន្តសេវាជូន។`;
  const STATUS = { safe: ["មិនទាន់ដល់ពេល", "Safe", "i-circle-check"], approaching: ["ជិតដល់ពេល", "Approaching", "i-clock"],
    due: ["ជិតផុត", "Expiring", "i-circle-alert"], expired: ["ផុតកំណត់", "Expired", "i-circle-alert"],
    sent: ["បានផ្ញើ", "Sent", "i-send"], invalid: ["កាលបរិច្ឆេទមិនត្រឹមត្រូវ", "Invalid", "i-circle-alert"] };
  const TITLES = { main: ["ផ្ទាំងគ្រប់គ្រង", "Manage and notify upcoming tracking expirations"],
    report: ["របាយការណ៍", "Daily send results, successes and failures"], users: ["អ្នកប្រើប្រាស់", "Admin accounts that can sign in"] };
  let sortKey = "", sortDir = "asc", dataVersion = null;
  let all = [], selected = new Set(), lastLog = 0, wasRunning = false, stats = {}, page = 1, total = 0, pages = 1, firstLoad = true;

  $("#phone").value = localStorage.getItem("phone") || $("#phone").value;   // remembered in this browser
  $("#phone").addEventListener("input", () => localStorage.setItem("phone", $("#phone").value.trim()));
  $("#tpl").value = localStorage.getItem("tpl2") || DEFAULT_TPL;
  $("#tpl").addEventListener("input", () => localStorage.setItem("tpl2", $("#tpl").value));

  const qs = () => new URLSearchParams({ normal: $("#normal").value, company: $("#company").value,
    filter: document.querySelector("input[name=f]:checked").value, q: $("#q").value.trim(), sort: sortKey, dir: sortDir }).toString();

  async function api(url, opt = {}) {
    const headers = { "X-CSRF-Token": csrf };
    if (typeof opt.body === "string") headers["Content-Type"] = "application/json";
    const res = await fetch(url, { credentials: "same-origin", ...opt, headers });
    if (res.status === 401) { location.href = "/login"; throw new Error("signed out"); }
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(j.error || `Request failed (HTTP ${res.status}) - server not responding or restarted`);
    return j;
  }
  const post = (path, body) => api(`${path}?${qs()}`, { method: "POST", body: JSON.stringify(body) });

  // ---------- small helpers ----------
  function addLog(l) {
    const log = $("#log"), line = document.createElement("div");
    line.className = l.level; line.textContent = `[${l.t}] ${l.msg}`;
    log.appendChild(line); log.scrollTop = log.scrollHeight;
  }
  let toastTimer;
  function toast(level, msg) {
    const t = $("#toast"); t.className = level; t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, level === "error" ? 12000 : 5000);
  }
  const say = (level, msg) => { addLog({ t: new Date().toLocaleTimeString("en-GB"), level, msg });
    if (level !== "info") { $("#progress").textContent = msg; toast(level, msg); } };
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  function td(tr, child, cls) {
    const c = document.createElement("td"); if (cls) c.className = cls;
    typeof child === "string" ? (c.textContent = child) : c.appendChild(child); tr.appendChild(c); return c;
  }
  const svgEl = (name, attrs = {}) => { const e = document.createElementNS(SVGNS, name); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };
  const icon = (name) => { const s = svgEl("svg", { class: "ic" }); s.appendChild(svgEl("use", { href: "#" + name })); return s; };
  const fmt = (iso) => { const p = (iso || "").split("-"); return p.length === 3 ? `${p[2]}-${p[1]}-${p[0]}` : "—"; };
  const hue = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.codePointAt(0)) >>> 0; return h % 6; };
  const initial = (s) => ((s || "?").replace(/^[@\-+]+/, "")[0] || "?").toUpperCase();
  const avatar = (name) => el("span", "avatar a" + hue(name), initial(name));
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  function setNum(sel, to) {  // count-up animation for the big numbers
    const e = $(sel), from = parseInt(e.dataset.v || "0", 10) || 0; e.dataset.v = to;
    if (reduced || from === to || Math.abs(to - from) < 2) { e.textContent = to.toLocaleString(); return; }
    const t0 = performance.now();
    const step = (t) => { const k = Math.min(1, (t - t0) / 450); e.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3))).toLocaleString();
      if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }

  // ---------- dashboard table ----------
  function skeleton() {
    const body = $("#rows"); body.replaceChildren();
    for (let i = 0; i < 8; i++) { const tr = document.createElement("tr");
      for (let k = 0; k < 8; k++) { const c = document.createElement("td"); if (k === 2 || k === 4 || k === 5) c.className = "hide-sm"; c.appendChild(el("span", "sk-bar")); tr.appendChild(c); }
      body.appendChild(tr); }
  }

  function render() {
    const rows = all, size = +$("#pageSize").value;
    const body = $("#rows"); body.replaceChildren();
    $("#empty").hidden = rows.length > 0;
    $("#emptyMsg").textContent = stats.units ? "No clients match your search or filter." : "No file loaded yet. Browse for an Excel file, or drag one onto this page.";
    $("#pick2").hidden = !!stats.units;
    const from = total ? (page - 1) * size + 1 : 0;
    $("#pageInfo").textContent = `Showing ${from.toLocaleString()}–${(from + rows.length - (total ? 1 : 0)).toLocaleString()} of ${total.toLocaleString()} results`;
    $("#pageNo").textContent = `${page} / ${pages}`; $("#prev").disabled = page <= 1; $("#next").disabled = page >= pages;
    for (const r of rows) {
      const tr = document.createElement("tr"); if (selected.has(r.id)) tr.className = "sel";
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = selected.has(r.id);
      cb.setAttribute("aria-label", "Select " + (r.user || r.plate));
      cb.addEventListener("change", () => { cb.checked ? selected.add(r.id) : selected.delete(r.id); tr.classList.toggle("sel", cb.checked); info(); });
      td(tr, cb, "ck");
      const u = el("div", "cell-user");
      if (r.user) u.append(avatar(r.user), el("span", "", r.user)); else u.append(el("span", "pill noid", "គ្មាន ID · No ID"));
      td(tr, u);
      td(tr, el("span", "mono", r.name || "—"), "hide-sm");
      td(tr, el("span", "pill " + (r.type.toLowerCase().startsWith("comp") ? "t-company" : "t-normal"), r.type), "hide-sm");
      td(tr, r.plate, "plate"); td(tr, el("span", "mono", r.imei), "hide-sm"); td(tr, fmt(r.expiry), "hide-sm");
      td(tr, r.days === null ? "—" : el("span", "pill d-" + r.state, r.days + " ថ្ងៃ"));
      const [km, en, ic] = STATUS[r.state], b = el("span", "badge b-" + r.state);
      b.append(icon(ic), `${km} (${en})`); td(tr, b);
      body.appendChild(tr);
    }
    info();
  }
  const info = () => {
    $("#selInfo").textContent = selected.size ? `${selected.size.toLocaleString()} selected` : "";
    $("#selClear").hidden = !selected.size; $("#selAll").hidden = total <= all.length || selected.size >= total;
  };

  // ---------- stats + donut ----------
  const SEGS = [["safe", "មិនទាន់ដល់ពេល · Safe"], ["approaching", "ជិតដល់ពេល · Approaching"], ["due", "ជិតផុត · Due"], ["expired", "ផុតកំណត់ · Expired"], ["sent", "បានផ្ញើ · Sent"]];
  function drawDonut(s) {
    const svg = $("#donut"), sum = SEGS.reduce((a, [k]) => a + (s[k] || 0), 0);
    svg.replaceChildren(svgEl("circle", { class: "track", cx: 21, cy: 21, r: 15.9155 }));
    let off = 0;
    if (sum) for (const [k] of SEGS) { const v = s[k] || 0; if (!v) continue; const pct = (v / sum) * 100;
      svg.appendChild(svgEl("circle", { class: "seg seg-" + k, cx: 21, cy: 21, r: 15.9155, "stroke-dasharray": `${Math.max(pct - 0.6, 0.4)} ${100 - Math.max(pct - 0.6, 0.4)}`, "stroke-dashoffset": -off })); off += pct; }
    const n = svgEl("text", { x: 21, y: 22.5, class: "dn" }); n.textContent = sum.toLocaleString();
    const l = svgEl("text", { x: 21, y: 27, class: "dl" }); l.textContent = "units";
    svg.append(n, l);
    $("#legend").replaceChildren(...SEGS.map(([k, label]) => { const li = el("li"); li.append(el("i", "sw seg-" + k), el("span", "", label), el("b", "", (s[k] || 0).toLocaleString())); return li; }));
  }
  function renderStats(s) {
    stats = s;
    setNum("#sUnits", s.units); $("#sUsers").textContent = s.users.toLocaleString();
    setNum("#sNormal", s.due_normal); setNum("#sCompany", s.due_company); setNum("#sSent", s.sent); $("#sExpired").textContent = s.expired.toLocaleString();
    drawDonut(s);
    $("#noIdCount").textContent = s.no_user ? s.no_user.toLocaleString() : "";
  }

  function applyData(d) {
    all = d.rows; total = d.total; page = d.page; pages = d.pages; $("#fileName").textContent = d.file || "No file loaded";
    renderStats(d.stats); firstLoad = false; render();
  }
  async function load() {
    for (const [id, v] of [["nLbl", "normal"], ["lblN", "normal"], ["cLbl", "company"], ["lblC", "company"]]) $("#" + id).textContent = $("#" + v).value;
    try { applyData(await api(`/api/data?${qs()}&page=${page}&size=${$("#pageSize").value}`)); }
    catch (e) { firstLoad = false; say("error", e.message); }
  }

  // ---------- live status ----------
  async function poll() {
    try {
      const s = await api("/api/status?since=" + lastLog);
      if (s.data_version !== undefined) {                                    // the list changed on the server -> refresh the table
        const changed = dataVersion !== null && s.data_version !== dataVersion; dataVersion = s.data_version;
        if (changed && !s.running && tab === "main") load();
      }
      s.logs.forEach((l) => { addLog(l); lastLog = l.id; });
      $("#stop").disabled = !s.running; $("#sendDue").disabled = $("#sendSel").disabled = s.running;
      $("#dot").classList.toggle("busy", s.running);
      const done = s.progress.sent + s.progress.failed;
      $("#runBanner").hidden = !s.running;
      if (s.running) {
        $("#progress").textContent = `កំពុងផ្ញើ… Sending ${done}/${s.progress.total}`;
        $("#runText").textContent = `កំពុងផ្ញើ… Sending ${done} of ${s.progress.total} clients · ${s.progress.sent} sent, ${s.progress.failed} failed`;
        $("#runBar").max = Math.max(s.progress.total, 1); $("#runBar").value = done;
      } else if (wasRunning) $("#progress").textContent = `Done · sent ${s.progress.sent}, failed ${s.progress.failed}`;
      if ((wasRunning && !s.running) || (s.running && s.logs.length)) { load(); if (tab === "report") loadReport(); }
      if (wasRunning && !s.running && tab !== "report") $("#viewRep").hidden = false;
      if (s.running) $("#viewRep").hidden = true;
      wasRunning = s.running;
    } catch (e) { /* transient */ }
  }

  async function send(mode) {
    const ids = [...selected];
    if (mode === "selected" && !ids.length) return say("warn", "Select at least one row first.");
    const force = $("#force").checked;
    let n;
    if (mode === "selected") n = ids.length;  // already-sent units are skipped by the server unless Force resend is on
    else n = stats.due + (force ? stats.due_resend : 0);
    if (!n) return say("warn", mode === "selected" ? "Selected units are already Sent. Turn on Force resend to send again." : "No clients are due right now.");
    const msg = force ? `FORCE RESEND is ON: ${n.toLocaleString()} unit(s) will be sent, including ones already sent before. Continue?`
                      : `Send reminders for ${n.toLocaleString()} unit(s)? (one message per client; units already Sent are skipped)`;
    if (!confirm(msg)) return;
    try {
      const r = await post("/api/send", { mode, ids, template: $("#tpl").value, limit: $("#limit").value, force, phone: $("#phone").value.trim() });
      $("#force").checked = false;  // safety: force mode switches itself off after each send
      say("info", `Started: ${r.started} client message(s) queued.` + (force ? " (force resend)" : ""));
      if (r.skipped) say("warn", `${r.skipped} plate(s) skipped, no Username/ID: ${r.skipped_names}. Use "Fill Username/ID".`);
    } catch (e) { say("error", e.message); }
  }

  $("#sendDue").onclick = () => send("due");
  $("#sendSel").onclick = () => send("selected");
  $("#stop").onclick = () => post("/api/stop", {}).catch((e) => say("error", e.message));
  $("#export").onclick = () => { location.href = "/api/export?" + qs(); };
  $("#preview").onclick = async () => {
    try {
      const ids = [...selected], r = await post("/api/preview", { mode: ids.length ? "selected" : "due", ids, template: $("#tpl").value, force: $("#force").checked, phone: $("#phone").value.trim() });
      $("#dlgText").textContent = r.text; const im = $("#dlgImg"); im.hidden = !r.image;
      if (r.image) im.src = "data:image/png;base64," + r.image;
      $("#dlgTo").textContent = `To: ${r.user} · ${r.units} unit(s) · ${r.images} image(s), the message goes with the last image` + (r.image ? "" : " · table image unavailable (text list will be sent)");
      $("#dlg").showModal();
    } catch (e) { say("error", e.message); }
  };
  $("#dlgClose").onclick = () => $("#dlg").close();
  $("#pick").onclick = () => $("#file").click();
  $("#pick2").onclick = () => $("#file").click();
  $("#dlTemplate").onclick = $("#dlTemplate2").onclick = () => { location.href = "/api/template"; };
  async function upload(f) {
    if (!f) return;
    if (!confirm(`Replace the current client list with "${f.name}"?`)) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      toast("warn", "Importing…");
      const r = await api(`/api/upload?normal=${$("#normal").value}&company=${$("#company").value}&size=${$("#pageSize").value}`, { method: "POST", body: fd });
      selected.clear(); $("#q").value = "";                                   // a leftover filter/search must not hide the new list
      document.querySelector("input[name=f][value=all]").checked = true;
      applyData(r.data);                                                      // show the new list right away (no refresh needed)
      if (r.warnings && r.warnings.length) say("warn", `Imported ${r.rows.toLocaleString()} row(s) from ${r.file}, but: ${r.warnings.join(" · ")}. Fix them in Excel and import again.`);
      else say("ok", `Imported ${r.rows.toLocaleString()} row(s) from ${r.file}.`);
    } catch (e) { say("error", e.message); }
  }
  $("#file").onchange = (ev) => { upload(ev.target.files[0]); ev.target.value = ""; };
  // drag a file from your computer anywhere onto the page
  addEventListener("dragover", (ev) => ev.preventDefault());
  addEventListener("drop", (ev) => { ev.preventDefault(); upload(ev.dataTransfer.files[0]); });
  $("#all").onchange = (ev) => { document.querySelectorAll("#rows input").forEach((c) => { if (c.checked !== ev.target.checked) c.click(); }); };
  let qTimer;
  $("#q").addEventListener("input", () => { clearTimeout(qTimer); qTimer = setTimeout(() => { page = 1; load(); }, 300); });
  document.querySelectorAll("input[name=f],#normal,#company").forEach((e) => e.addEventListener("change", () => { page = 1; load(); }));
  $("#pageSize").onchange = () => { page = 1; load(); };
  $("#prev").onclick = () => { if (page > 1) { page--; load(); } };
  $("#next").onclick = () => { if (page < pages) { page++; load(); } };
  $("#selClear").onclick = () => { selected.clear(); render(); };
  $("#selAll").onclick = async () => {
    try { const d = await api("/api/ids?" + qs()); d.ids.forEach((i) => selected.add(i)); render(); say("ok", `${selected.size.toLocaleString()} units selected.`); }
    catch (e) { say("error", e.message); }
  };

  // ---------- sort by column ----------
  function paintSort() {
    document.querySelectorAll("th[data-sort]").forEach((h) => { h.classList.toggle("asc", h.dataset.sort === sortKey && sortDir === "asc");
      h.classList.toggle("desc", h.dataset.sort === sortKey && sortDir === "desc"); });
  }
  document.querySelectorAll("th[data-sort]").forEach((h) => h.addEventListener("click", () => {
    if (sortKey === h.dataset.sort) { if (sortDir === "asc") sortDir = "desc"; else { sortKey = ""; sortDir = "asc"; } }
    else { sortKey = h.dataset.sort; sortDir = "asc"; }
    page = 1; paintSort(); load();
  }));

  // ---------- admin tools: new expiry date / fill Username-ID ----------
  const showErr = (id, msg) => { const e = $(id); e.textContent = msg || ""; e.hidden = !msg; };
  $("#btnExp").onclick = () => {
    if (!selected.size) return say("warn", "Select plates first (search a Name such as WL012, then 'Select all matching').");
    $("#expInfo").textContent = `${selected.size.toLocaleString()} plate(s) selected.`; $("#expDate").value = ""; showErr("#expErr"); $("#expDlg").showModal();
  };
  $("#expCancel").onclick = () => $("#expDlg").close();
  $("#expSave").onclick = async () => {
    if (!$("#expDate").value) return showErr("#expErr", "Choose the new expiry date.");
    try {
      const r = await api("/api/update_expiry", { method: "POST", body: JSON.stringify({ ids: [...selected], expiry_date: $("#expDate").value }) });
      $("#expDlg").close(); selected.clear(); say("ok", `New expiry date ${fmt($("#expDate").value)} saved on ${r.updated.toLocaleString()} plate(s).`); load();
    } catch (e) { showErr("#expErr", e.message); }
  };
  let nameMap = {};
  $("#btnFill").onclick = async () => {
    $("#fillName").value = $("#q").value.trim(); $("#fillUser").value = ""; showErr("#fillErr"); $("#fillInfo").textContent = "Type a Name. Every plate with this Name gets the Username/ID.";
    try {
      const d = await api("/api/names"); nameMap = {};
      $("#nameList").replaceChildren(...d.names.map((n) => { nameMap[n.name.toLowerCase()] = n; const o = document.createElement("option"); o.value = n.name; o.label = `${n.plates} plate(s)`; return o; }));
    } catch (e) { /* the list is only a help */ }
    fillHint(); $("#fillDlg").showModal();
  };
  function fillHint() {
    const n = nameMap[$("#fillName").value.trim().toLowerCase()];
    if (n) $("#fillInfo").textContent = `${n.plates} plate(s) have this Name, ${n.with_user} already have a Username/ID.`;
  }
  $("#fillName").addEventListener("input", fillHint);
  $("#fillCancel").onclick = () => $("#fillDlg").close();
  $("#fillSave").onclick = async () => {
    const name = $("#fillName").value.trim(), user = $("#fillUser").value.trim();
    if (!name || !user) return showErr("#fillErr", "Enter the Name and the Username/ID.");
    const n = nameMap[name.toLowerCase()];
    if (n && n.with_user && !confirm(`${n.with_user} of ${n.plates} plate(s) named ${name} already have a Username/ID. Replace all with ${user}?`)) return;
    try {
      const r = await api("/api/set_user", { method: "POST", body: JSON.stringify({ name, user }) });
      $("#fillDlg").close(); say("ok", `Username/ID ${user} applied to ${r.updated.toLocaleString()} plate(s) named ${name}.`); load();
    } catch (e) { showErr("#fillErr", e.message); }
  };

  // ---------- tabs ----------
  let tab = "main";
  const VIEWS = { main: ["#viewMain", "#tabMain"], report: ["#viewReport", "#tabReport"], users: ["#viewUsers", "#tabUsers"] };
  function show(t) {
    tab = t;
    for (const [k, [v, b]] of Object.entries(VIEWS)) { $(v).hidden = k !== t; $(b).classList.toggle("on", k === t); }
    $("#pageTitle").textContent = TITLES[t][0]; $("#pageSub").textContent = TITLES[t][1];
    document.querySelector(".dock-btns").hidden = t !== "main";   // send buttons only on the Dashboard
    if (t === "report") { $("#viewRep").hidden = true; loadReport(); }
    if (t === "users") loadUsers();
    scrollTo({ top: 0 });
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
  $("#viewRep").onclick = () => { setRange("today", false); show("report"); };

  // ---------- report (by day + status) ----------
  const RSTATUS = { sent: ["ជោគជ័យ", "Success", "i-circle-check"], failed: ["បរាជ័យ", "Failed", "i-circle-x"], skipped: ["មិនបានផ្ញើ", "Skipped", "i-clock"] };
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  function setRange(kind, reload = true) {
    const to = new Date(), from = new Date();
    if (kind === "7") from.setDate(from.getDate() - 6);
    if (kind === "30") from.setDate(from.getDate() - 29);
    $("#rFrom").value = kind === "all" ? "" : iso(from); $("#rTo").value = kind === "all" ? "" : iso(to);
    document.querySelectorAll("[data-range]").forEach((b) => b.classList.toggle("on", b.dataset.range === kind));
    if (reload) loadReport();
  }
  const rq = () => {
    const p = new URLSearchParams({ status: document.querySelector("input[name=rf]:checked").value, from: $("#rFrom").value, to: $("#rTo").value });
    if (!$("#rFrom").value && !$("#rTo").value) p.set("all", "1");
    return p.toString();
  };
  function pickDay(day) { $("#rFrom").value = $("#rTo").value = day; document.querySelectorAll("[data-range]").forEach((b) => b.classList.remove("on")); loadReport(); }

  function drawChart(days) {
    const svg = $("#dayChart"), data = [...days].reverse().slice(-31);   // oldest -> newest
    svg.replaceChildren(); svg.toggleAttribute("hidden", !data.length);  /* SVG elements have no .hidden property */ $("#chartEmpty").hidden = data.length > 0;
    if (!data.length) return;
    const W = 640, H = 200, L = 30, B = 24, T = 10, plotW = W - L - 8, plotH = H - B - T, max = Math.max(...data.map((d) => d.total), 1);
    for (const f of [0, 0.5, 1]) { const y = T + plotH * (1 - f);
      svg.appendChild(svgEl("line", { class: "grid", x1: L, x2: W - 8, y1: y, y2: y }));
      const t = svgEl("text", { x: L - 6, y: y + 3, "text-anchor": "end" }); t.textContent = Math.round(max * f); svg.appendChild(t); }
    const step = plotW / data.length, bw = Math.min(42, step * 0.62), every = Math.ceil(data.length / 8);
    data.forEach((d, i) => {
      const x = L + step * i + (step - bw) / 2, g = svgEl("g", { class: "bar" }); let y = T + plotH;
      const tip = svgEl("title"); tip.textContent = `${d.day}: ${d.sent} success, ${d.failed} failed, ${d.skipped} skipped`; g.appendChild(tip);
      for (const [k, cls] of [["sent", "b-s"], ["failed", "b-f"], ["skipped", "b-k"]]) { const h = (d[k] / max) * plotH; if (!h) continue; y -= h;
        g.appendChild(svgEl("rect", { class: cls, x, y, width: bw, height: h, rx: 3 })); }
      g.appendChild(svgEl("rect", { x, y: T, width: bw, height: plotH, fill: "transparent" }));
      g.addEventListener("click", () => pickDay(d.day)); svg.appendChild(g);
      if (i % every === 0 || i === data.length - 1) { const t = svgEl("text", { x: x + bw / 2, y: H - 7, "text-anchor": "middle" }); t.textContent = d.day.slice(5); svg.appendChild(t); }
    });
  }

  async function loadReport() {
    try {
      const d = await api("/api/report?" + rq()), m = d.summary;
      if (d.keep_from) { $("#rFrom").min = $("#rTo").min = d.keep_from; $("#keepNote").textContent = `Report keeps the last 3 months (from ${d.keep_from}); older days are removed automatically.`; }
      setNum("#rTotal", m.total); setNum("#rSent", m.sent); setNum("#rFailed", m.failed); setNum("#rSkipped", m.skipped);
      $("#rClients").textContent = m.clients_sent.toLocaleString(); $("#rRate").textContent = (m.total ? Math.round((m.sent / m.total) * 100) : 0) + "% success";
      drawChart(d.days);
      const dr = $("#dRows"); dr.replaceChildren(); $("#dEmpty").hidden = d.days.length > 0;
      for (const x of d.days) {
        const tr = document.createElement("tr"); tr.className = "click"; tr.title = "Show this day";
        td(tr, x.day); td(tr, String(x.total)); td(tr, String(x.sent), "ok"); td(tr, String(x.failed), x.failed ? "bad" : "");
        td(tr, String(x.skipped), x.skipped ? "warn" : ""); td(tr, (x.total ? Math.round((x.sent / x.total) * 100) : 0) + "%");
        tr.addEventListener("click", () => pickDay(x.day)); dr.appendChild(tr);
      }
      const body = $("#rRows"); body.replaceChildren();
      $("#rEmpty").hidden = d.rows.length > 0; $("#rCount").textContent = d.rows.length.toLocaleString();
      for (const r of d.rows) {
        const tr = document.createElement("tr");
        td(tr, r.ts); const u = el("div", "cell-user"); u.append(avatar(r.user), el("span", "", r.user)); td(tr, u);
        td(tr, String(r.units), "hide-sm"); td(tr, r.plates || "—", "hide-sm");
        const [km, en, ic] = RSTATUS[r.status] || ["", r.status, "i-circle-alert"], b = el("span", "badge b-" + r.status);
        b.append(icon(ic), `${km} (${en})`); td(tr, b);
        const why = td(tr, r.reason || "—", "why " + (r.status === "failed" ? "bad" : r.status === "skipped" ? "skip" : ""));
        if (r.detail) why.title = r.detail;  // technical detail on hover
        td(tr, r.sent_by || "—", "hide-sm"); body.appendChild(tr);
      }
    } catch (e) { say("error", e.message); }
  }
  document.querySelectorAll("input[name=rf]").forEach((e) => e.addEventListener("change", loadReport));
  $("#rFrom").addEventListener("change", loadReport); $("#rTo").addEventListener("change", loadReport);
  document.querySelectorAll("[data-range]").forEach((b) => b.addEventListener("click", () => setRange(b.dataset.range)));
  $("#rExport").onclick = () => { location.href = "/api/report/export?" + rq(); };
  setRange("7", false);

  // ---------- admin users ----------
  let dlgMode = null, dlgUser = null;
  async function loadUsers() {
    try {
      const d = await api("/api/users"), body = $("#uRows"); body.replaceChildren();
      for (const u of d.users) {
        const tr = document.createElement("tr");
        const c = el("div", "cell-user"); c.append(avatar(u.username), el("span", "", u.username + (u.me ? "  (you)" : ""))); td(tr, c);
        td(tr, el("span", "badge " + (u.active ? "b-sent" : "b-failed"), u.active ? "Active" : "Disabled"));
        td(tr, u.created_at || "—", "hide-sm"); td(tr, u.last_login || "—", "hide-sm");
        const box = el("div", "row-btns"), act = (label, cls, fn) => { const b = el("button", "btn sm " + cls, label); b.type = "button"; b.onclick = fn; box.appendChild(b); };
        act("Reset password", "", () => openDlg("reset", u));
        if (!u.me) {
          act(u.active ? "Disable" : "Enable", "", async () => { try { await api(`/api/users/${u.id}/active`, { method: "POST", body: JSON.stringify({ active: !u.active }) }); loadUsers(); } catch (e) { say("error", e.message); } });
          act("Delete", "danger", async () => { if (!confirm(`Delete user "${u.username}"?`)) return; try { await api(`/api/users/${u.id}/delete`, { method: "POST", body: "{}" }); loadUsers(); } catch (e) { say("error", e.message); } });
        }
        td(tr, box); body.appendChild(tr);
      }
    } catch (e) { say("error", e.message); }
  }
  function openDlg(mode, u) {
    dlgMode = mode; dlgUser = u; $("#uErr").hidden = true; $("#uPass").value = "";
    $("#uTitle").textContent = mode === "add" ? "Add admin user" : `Reset password: ${u.username}`;
    $("#uName").value = u ? u.username : ""; $("#uName").disabled = mode !== "add";
    $("#uDlg").showModal(); (mode === "add" ? $("#uName") : $("#uPass")).focus();
  }
  async function saveDlg() {
    try {
      if (dlgMode === "add") await api("/api/users", { method: "POST", body: JSON.stringify({ username: $("#uName").value, password: $("#uPass").value }) });
      else await api(`/api/users/${dlgUser.id}/password`, { method: "POST", body: JSON.stringify({ password: $("#uPass").value }) });
      $("#uDlg").close(); say("ok", dlgMode === "add" ? "User created." : "Password changed."); loadUsers();
    } catch (e) { $("#uErr").textContent = e.message; $("#uErr").hidden = false; }
  }
  $("#uAdd").onclick = () => openDlg("add", null);
  $("#uSave").onclick = saveDlg; $("#uCancel").onclick = () => $("#uDlg").close();
  $("#uPass").addEventListener("keydown", (ev) => { if (ev.key === "Enter") saveDlg(); });

  skeleton(); load(); poll(); setInterval(poll, 2000);
})();

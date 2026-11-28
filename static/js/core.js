// Shared basics: $, tt (translate), api/post helpers, toast/log, DOM helpers, permissions, remembered phone/template.
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
  const $ = (s) => document.querySelector(s);
  const tt = (k, v) => I18N.t(k, v);                     // translate (English / Khmer, chosen with the language button)
  const csrf = $('meta[name=csrf]').content;
  const SVGNS = "http://www.w3.org/2000/svg";
  const DEFAULT_TPL = `សួស្តីបង! គណនី GPS របស់បង ({count} គ្រឿង) នឹងផុតកំណត់នៅថ្ងៃទី {expiry_date}\n\nសូមបងទំនាក់ទំនងបន្តសេវាតាមរយៈលេខទំនាក់ទំនង {phone} (Call / Telegram)។\n\nសូមបងទំនាក់ទំនងបន្តសេវាអោយបានមុនថ្ងៃផុតកំណត់ ជៀសវាងការផ្អាកការប្រើប្រាស់បណ្ដោះអាសន្ន និងការបន្តសេវាមិនបានជោគជ័យដោយសារក្រុមហ៊ុនស៊ីមកាតមិនបន្តសេវាជូន។`;
  const STATUS = { safe: "i-circle-check", approaching: "i-clock", due: "i-circle-alert", expired: "i-circle-alert", sent: "i-send", invalid: "i-circle-alert" };
  const TITLES = { main: [tt("ផ្ទាំងគ្រប់គ្រង"), tt("Manage and notify upcoming tracking expirations")],
    report: [tt("របាយការណ៍"), tt("Daily send results, successes and failures")], users: [tt("អ្នកប្រើប្រាស់"), tt("Admin accounts that can sign in")] };
  const PERMS = new Set((document.querySelector("meta[name=perms]").content || "").split(",").filter(Boolean));
  const can = (p) => PERMS.has(p);
  document.querySelectorAll("[data-perm]").forEach((e) => { if (!can(e.dataset.perm)) e.hidden = true; });   // the server checks every action again
  let sortKey = "", sortDir = "asc", dataVersion = null;
  let all = [], selected = new Set(), lastLog = 0, wasRunning = false, stats = {}, page = 1, total = 0, pages = 1, firstLoad = true;

  $("#phone").value = localStorage.getItem("phone") || $("#phone").value;   // remembered in this browser
  $("#phone").addEventListener("input", () => localStorage.setItem("phone", $("#phone").value.trim()));
  $("#tpl").value = localStorage.getItem("tpl2") || DEFAULT_TPL;
  $("#tpl").addEventListener("input", () => localStorage.setItem("tpl2", $("#tpl").value));

  const qs = () => new URLSearchParams({ normal: $("#normal").value, company: $("#company").value, rental: $("#rental").value,
    filter: document.querySelector("input[name=f]:checked").value, q: $("#q").value.trim(), sort: sortKey, dir: sortDir,
    utype: $("#utype").value, dmin: $("#dmin").value.trim(), dmax: $("#dmax").value.trim() }).toString();

  async function api(url, opt = {}) {
    const headers = { "X-CSRF-Token": csrf };
    if (typeof opt.body === "string") headers["Content-Type"] = "application/json";
    const res = await fetch(url, { credentials: "same-origin", ...opt, headers });
    if (res.status === 401) { location.href = "/login"; throw new Error("signed out"); }
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(j.error ? tt(j.error) : tt("Request failed (HTTP {n}) - server not responding or restarted", { n: res.status }));
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

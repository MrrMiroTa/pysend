// Report: by day + status, master -> detail, admin changes.
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
  // ---------- report (by day + status) ----------
  const RSTATUS = { sent: "i-circle-check", failed: "i-circle-x", skipped: "i-clock" };
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  function setRange(kind, reload = true) {
    const to = new Date(), from = new Date();
    if (kind === "7") from.setDate(from.getDate() - 6);
    if (kind === "30") from.setDate(from.getDate() - 29);
    $("#rFrom").value = kind === "all" ? "" : iso(from); $("#rTo").value = kind === "all" ? "" : iso(to);
    document.querySelectorAll("[data-range]").forEach((b) => b.classList.toggle("on", b.dataset.range === kind));
    if (reload) loadReport();
  }
  const CHANGE_LABEL = { expiry: tt("ថ្ងៃផុតកំណត់ (Expiry date)"), user: tt("Username/ID"), import: tt("Import file") };
  const rq = () => {
    const p = new URLSearchParams({ status: document.querySelector("input[name=rf]:checked").value, from: $("#rFrom").value, to: $("#rTo").value });
    if (!$("#rFrom").value && !$("#rTo").value) p.set("all", "1");
    p.set("ctype", document.querySelector("input[name=cf]:checked").value); p.set("cq", $("#cQ").value.trim());
    p.set("imei", $("#rImei").value.trim()); p.set("ruser", $("#rUser").value.trim());
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
      const tip = svgEl("title"); tip.textContent = tt("{day}: {s} success, {f} failed, {k} skipped", { day: d.day, s: d.sent, f: d.failed, k: d.skipped }); g.appendChild(tip);
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
      if (d.keep_from) { $("#rFrom").min = $("#rTo").min = d.keep_from; $("#keepNote").textContent = tt("Report keeps the last 3 months (from {d}); older days are removed automatically.", { d: d.keep_from }); }
      setNum("#rTotal", m.total); setNum("#rSent", m.sent); setNum("#rFailed", m.failed); setNum("#rSkipped", m.skipped);
      $("#rClients").textContent = m.clients_sent.toLocaleString(); $("#rRate").textContent = tt("{n}% success", { n: m.total ? Math.round((m.sent / m.total) * 100) : 0 });
      drawChart(d.days);
      const dr = $("#dRows"); dr.replaceChildren(); $("#dEmpty").hidden = d.days.length > 0;
      for (const x of d.days) {
        const tr = document.createElement("tr"); tr.className = "click"; tr.title = tt("Show this day");
        td(tr, x.day); td(tr, String(x.total)); td(tr, String(x.sent), "ok"); td(tr, String(x.failed), x.failed ? "bad" : "");
        td(tr, String(x.skipped), x.skipped ? "warn" : ""); td(tr, (x.total ? Math.round((x.sent / x.total) * 100) : 0) + "%");
        tr.addEventListener("click", () => pickDay(x.day)); dr.appendChild(tr);
      }
      const mb = $("#mRows"); mb.replaceChildren(); $("#mEmpty").hidden = d.master.length > 0; $("#mCount").textContent = d.master.length.toLocaleString();
      for (const m of d.master) {                                           // Report master: one line per send
        const tr = document.createElement("tr");
        td(tr, m.ts); td(tr, el("span", "kind", m.kind === "auto" ? tt("Auto") : tt("Manual")));
        td(tr, m.period ? tt("{n} days", { n: m.period }) : "—");
        const ms = el("div", "", String(m.sent)); if (m.failed) ms.append(el("span", "cnt-fail", tt("{n} fail", { n: m.failed }))); if (m.skipped) ms.append(el("span", "cnt-fail", tt("{n} skipped", { n: m.skipped })));
        td(tr, ms); td(tr, String(m.clients));
        const b = el("button", "btn sm", tt("Detail")); b.type = "button"; b.onclick = () => openDetail(m); td(tr, b);
        mb.appendChild(tr);
      }
      const body = $("#rRows"); body.replaceChildren();
      $("#rEmpty").hidden = d.rows.length > 0; $("#rCount").textContent = d.rows.length.toLocaleString();
      for (const r of d.rows) {
        const tr = document.createElement("tr");
        td(tr, r.ts); const u = el("div", "cell-user"); u.append(avatar(r.user), el("span", "", r.user)); td(tr, u);
        td(tr, String(r.units), "hide-sm"); td(tr, r.plates || "—", "hide-sm");
        const b = el("span", "badge b-" + r.status);
        b.append(icon(RSTATUS[r.status] || "i-circle-alert"), tt("rs." + r.status)); td(tr, b);
        const why = td(tr, r.reason || "—", "why " + (r.status === "failed" ? "bad" : r.status === "skipped" ? "skip" : ""));
        if (r.detail) why.title = r.detail;  // technical detail on hover
        td(tr, r.sent_by || "—", "hide-sm"); body.appendChild(tr);
      }
      const cb = $("#cRows"); cb.replaceChildren();                       // what the admins changed: master, one line per action
      $("#cEmpty").hidden = d.change_groups.length > 0; $("#cCount").textContent = d.change_groups.length.toLocaleString();
      for (const c of d.change_groups) {
        const tr = document.createElement("tr"), isDate = c.action === "expiry";
        td(tr, c.ts); td(tr, c.actor || "—"); td(tr, CHANGE_LABEL[c.action] || c.action);
        td(tr, c.action === "import" ? "—" : (c.names.join(", ") + (c.count > c.names.length ? " …" : "")) || "—", "hide-sm");
        td(tr, String(c.count));
        const val = c.action === "import" ? c.note : (c.new ? `${(isDate ? fmt(c.old) : c.old) || "—"} → ${isDate ? fmt(c.new) : c.new}` : "");
        td(tr, val || "—", "hide-sm");
        const b = el("button", "btn sm", tt("Detail")); b.type = "button"; b.onclick = () => openChange(c); td(tr, b);
        cb.appendChild(tr);
      }
    } catch (e) { say("error", e.message); }
  }
  document.querySelectorAll("input[name=rf], input[name=cf]").forEach((e) => e.addEventListener("change", loadReport));
  let iTimer; for (const id of ["#rImei", "#rUser"]) $(id).addEventListener("input", () => { clearTimeout(iTimer); iTimer = setTimeout(loadReport, 350); });

  // ---------- report master -> detail (Paid Off / Rental) ----------
  function fillUnits(body, emptyEl, countEl, sec) {
    const list = sec.rows;
    body.replaceChildren(); emptyEl.hidden = list.length > 0; countEl.textContent = tt("· Client (Count): {c} · {n} plate(s)", { c: sec.clients.toLocaleString(), n: list.length.toLocaleString() });
    for (const u of list) {
      const tr = document.createElement("tr"), who = el("div", "", u.name || u.user || "—"); if (u.name && u.user) who.append(el("small", "note", u.user));
      td(tr, who); td(tr, u.plate || "—"); td(tr, el("span", "mono", u.imei || "—")); td(tr, fmt(u.expiry));
      const b = el("span", "badge b-" + u.status); b.append(icon(RSTATUS[u.status] || "i-circle-alert"), tt("rs." + u.status)); td(tr, b);
      body.appendChild(tr);
    }
  }
  async function openDetail(m) {
    try {
      const q = new URLSearchParams({ day: m.day, batch: m.batch, imei: $("#rImei").value.trim(), ruser: $("#rUser").value.trim() });
      const d = await api("/api/report/detail?" + q);
      $("#rdTitle").textContent = tt("Detail · {ts} · {kind}", { ts: m.ts, kind: m.kind === "auto" ? tt("Auto") : tt("Manual") });
      $("#rdInfo").textContent = tt("Period {p} days · {s} sent · {c} client(s)", { p: m.period || "—", s: m.sent, c: m.clients });
      fillUnits($("#rdPaid"), $("#rdPaidE"), $("#rdPaidN"), d.paid_off); fillUnits($("#rdRent"), $("#rdRentE"), $("#rdRentN"), d.rental);
      $("#rdDlg").showModal();
    } catch (e) { say("error", e.message); }
  }
  $("#rdClose").onclick = () => $("#rdDlg").close();
  async function openChange(c) {
    try {
      const d = await api("/api/report/change_detail?" + new URLSearchParams({ ts: c.ts, actor: c.actor, action: c.action })), isDate = c.action === "expiry";
      $("#cdTitle").textContent = `${CHANGE_LABEL[c.action] || c.action} · ${c.ts}`; $("#cdInfo").textContent = tt("Admin: {a} · {n} item(s)", { a: c.actor || "—", n: d.rows.length.toLocaleString() });
      const body = $("#cdRows"); body.replaceChildren();
      for (const r of d.rows) { const tr = document.createElement("tr");
        td(tr, r.name || "—"); td(tr, r.plate || "—"); td(tr, (isDate ? fmt(r.old_value) : r.old_value) || "—", "muted"); td(tr, (isDate ? fmt(r.new_value) : r.new_value) || "—"); body.appendChild(tr); }
      $("#cdDlg").showModal();
    } catch (e) { say("error", e.message); }
  }
  $("#cdClose").onclick = () => $("#cdDlg").close();
  let cTimer; $("#cQ").addEventListener("input", () => { clearTimeout(cTimer); cTimer = setTimeout(loadReport, 300); });
  $("#rFrom").addEventListener("change", loadReport); $("#rTo").addEventListener("change", loadReport);
  document.querySelectorAll("[data-range]").forEach((b) => b.addEventListener("click", () => setRange(b.dataset.range)));
  $("#rExport").onclick = () => { location.href = "/api/report/export?" + rq(); };
  setRange("7", false);

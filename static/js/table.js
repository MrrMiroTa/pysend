// Dashboard table, status cards and donut chart.
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
  // ---------- dashboard table ----------
  function skeleton() {
    const body = $("#rows"); body.replaceChildren();
    for (let i = 0; i < 8; i++) { const tr = document.createElement("tr");
      for (let k = 0; k < 9; k++) { const c = document.createElement("td"); if (k === 2 || k === 3 || k === 5 || k === 6) c.className = "hide-sm"; c.appendChild(el("span", "sk-bar")); tr.appendChild(c); }
      body.appendChild(tr); }
  }

  function render() {
    const rows = all, size = +$("#pageSize").value;
    const body = $("#rows"); body.replaceChildren();
    $("#empty").hidden = rows.length > 0;
    $("#emptyMsg").textContent = stats.units ? tt("No clients match your search or filter.") : tt("No file loaded yet. Browse for an Excel file, or drag one onto this page.");
    $("#pick2").hidden = !!stats.units;
    const from = total ? (page - 1) * size + 1 : 0;
    $("#pageInfo").textContent = tt("Showing {from}–{to} of {total} results", { from: from.toLocaleString(), to: (from + rows.length - (total ? 1 : 0)).toLocaleString(), total: total.toLocaleString() });
    $("#pageNo").textContent = `${page} / ${pages}`; $("#prev").disabled = page <= 1; $("#next").disabled = page >= pages;
    for (const r of rows) {
      const tr = document.createElement("tr"); if (selected.has(r.id)) tr.className = "sel";
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = selected.has(r.id);
      cb.setAttribute("aria-label", "Select " + (r.user || r.plate));
      cb.addEventListener("change", () => { cb.checked ? selected.add(r.id) : selected.delete(r.id); tr.classList.toggle("sel", cb.checked); info(); });
      td(tr, cb, "ck");
      const u = el("div", "cell-user");
      if (r.user) u.append(avatar(r.user), el("span", "", r.user)); else u.append(el("span", "pill noid", tt("No ID")));
      td(tr, u);
      td(tr, el("span", "mono", r.name || "—"), "hide-sm");
      td(tr, el("span", "pill " + (r.type.toLowerCase().startsWith("comp") ? "t-company" : "t-normal"), r.type), "hide-sm");
      td(tr, el("span", "pill " + (r.user_type === "rental" ? "t-rental" : "t-paid"), r.user_type === "rental" ? tt("Rental") : tt("Paid off")), "hide-sm");
      td(tr, r.plate, "plate"); td(tr, el("span", "mono", r.imei), "hide-sm"); const ex = el("div", "", fmt(r.expiry)); if (r.note) ex.append(el("small", "note", r.note)); ex.title = r.note || ""; td(tr, ex, "hide-sm");
      td(tr, r.days === null ? "—" : el("span", "pill d-" + r.state, tt("{n} days", { n: r.days })));
      const b = el("span", "badge b-" + r.state);
      b.append(icon(STATUS[r.state]), tt("st." + r.state)); td(tr, b);
      body.appendChild(tr);
    }
    info();
  }
  const info = () => {
    $("#selInfo").textContent = selected.size ? tt("{n} selected", { n: selected.size.toLocaleString() }) : "";
    $("#selClear").hidden = !selected.size; $("#selAll").hidden = total <= all.length || selected.size >= total;
  };

  // ---------- stats + donut ----------
  const SEGS = ["safe", "approaching", "due", "expired", "sent"].map((k) => [k, tt("SEG." + k)]);
  function drawDonut(s) {
    const svg = $("#donut"), sum = SEGS.reduce((a, [k]) => a + (s[k] || 0), 0);
    svg.replaceChildren(svgEl("circle", { class: "track", cx: 21, cy: 21, r: 15.9155 }));
    let off = 0;
    if (sum) for (const [k] of SEGS) { const v = s[k] || 0; if (!v) continue; const pct = (v / sum) * 100;
      svg.appendChild(svgEl("circle", { class: "seg seg-" + k, cx: 21, cy: 21, r: 15.9155, "stroke-dasharray": `${Math.max(pct - 0.6, 0.4)} ${100 - Math.max(pct - 0.6, 0.4)}`, "stroke-dashoffset": -off })); off += pct; }
    const n = svgEl("text", { x: 21, y: 22.5, class: "dn" }); n.textContent = sum.toLocaleString();
    const l = svgEl("text", { x: 21, y: 27, class: "dl" }); l.textContent = tt("units");
    svg.append(n, l);
    $("#legend").replaceChildren(...SEGS.map(([k, label]) => { const li = el("li"); li.append(el("i", "sw seg-" + k), el("span", "", label), el("b", "", (s[k] || 0).toLocaleString())); return li; }));
  }
  function renderStats(s) {
    stats = s;
    setNum("#sUnits", s.units); $("#sUsers").textContent = s.users.toLocaleString();
    setNum("#sSafe", s.safe); setNum("#sApp", s.approaching); setNum("#sDue", s.due);
    $("#sSent").textContent = s.sent.toLocaleString(); $("#sExpired").textContent = s.expired.toLocaleString();
    $("#sPaid").textContent = s.paid_off.toLocaleString(); $("#sRental").textContent = s.rental.toLocaleString();
    $("#sReady").textContent = s.ready.toLocaleString(); $("#sResend").textContent = s.ready_resend.toLocaleString();
    drawDonut(s);
    $("#noIdCount").textContent = s.no_user ? s.no_user.toLocaleString() : "";
  }

  function applyData(d) {
    all = d.rows; total = d.total; page = d.page; pages = d.pages; $("#fileName").textContent = d.file || tt("No file loaded");
    renderStats(d.stats); firstLoad = false; render();
    let lo = $("#dmin").value.trim(), hi = $("#dmax").value.trim();                  // days-left range: show how many units match
    if (lo !== "" && hi !== "" && +lo > +hi) [lo, hi] = [hi, lo];                   // 3 → 1 works like 1 → 3
    $("#rangeClear").hidden = !(lo || hi);
    $("#rangeInfo").textContent = (lo || hi) ? tt("Days left {lo}–{hi}: {n} unit(s)", { lo: lo || "…", hi: hi || "…", n: d.total.toLocaleString() }) : "";
  }
  async function load() {
    try { applyData(await api(`/api/data?${qs()}&page=${page}&size=${$("#pageSize").value}`)); }
    catch (e) { firstLoad = false; say("error", e.message); }
  }

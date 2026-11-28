// Live status polling, send / preview / import / selection / filters (Dashboard buttons).
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
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
        $("#progress").textContent = tt("Sending {done}/{total}", { done, total: s.progress.total });
        $("#runText").textContent = tt("Sending {done} of {total} clients · {sent} sent, {failed} failed", { done, total: s.progress.total, sent: s.progress.sent, failed: s.progress.failed });
        $("#runBar").max = Math.max(s.progress.total, 1); $("#runBar").value = done;
      } else if (wasRunning) $("#progress").textContent = tt("Done · sent {sent}, failed {failed}", { sent: s.progress.sent, failed: s.progress.failed });
      if ((wasRunning && !s.running) || (s.running && s.logs.length)) { load(); if (tab === "report" && can("report")) loadReport(); }
      if (wasRunning && !s.running && tab !== "report" && can("report")) $("#viewRep").hidden = false;
      if (s.running) $("#viewRep").hidden = true;
      wasRunning = s.running;
    } catch (e) { /* transient */ }
  }

  async function send(mode) {
    const ids = [...selected];
    if (mode === "selected" && !ids.length) return say("warn", tt("Select at least one row first."));
    const force = $("#force").checked;
    let n;
    if (mode === "selected") n = ids.length;  // already-sent units are skipped by the server unless Force resend is on
    else n = stats.ready + (force ? stats.ready_resend : 0);
    if (!n) return say("warn", tt(mode === "selected" ? "Selected units are already Sent. Turn on Force resend to send again." : "No clients are due right now."));
    const msg = force ? tt("FORCE RESEND is ON: {n} unit(s) will be sent, including ones already sent before. Continue?", { n: n.toLocaleString() })
                      : tt("Send reminders for {n} unit(s)? (one message per client; units already Sent are skipped)", { n: n.toLocaleString() });
    if (!confirm(msg)) return;
    try {
      const r = await post("/api/send", { mode, ids, template: $("#tpl").value, limit: $("#limit").value, force, phone: $("#phone").value.trim() });
      $("#force").checked = false;  // safety: force mode switches itself off after each send
      say("info", tt("Started: {n} client message(s) queued.", { n: r.started }) + (force ? tt(" (force resend)") : ""));
      if (r.skipped) say("warn", tt("{n} plate(s) skipped, no Username/ID: {names}. Use \"Fill Username/ID\".", { n: r.skipped, names: r.skipped_names }));
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
      $("#dlgTo").textContent = tt("To: {user} · {units} unit(s) · {images} image(s), the message goes with the last image", { user: r.user, units: r.units, images: r.images }) + (r.image ? "" : tt(" · table image unavailable (text list will be sent)"));
      $("#dlg").showModal();
    } catch (e) { say("error", e.message); }
  };
  $("#dlgClose").onclick = () => $("#dlg").close();
  let importMode = "merge";                                                 // merge = add new rows, skip duplicate IMEI
  $("#pick").onclick = () => { importMode = "merge"; $("#file").click(); };
  $("#pick2").onclick = () => { importMode = "merge"; $("#file").click(); };
  $("#pickReplace").onclick = () => { importMode = "replace"; $("#file").click(); };
  $("#dlTemplate").onclick = $("#dlTemplate2").onclick = () => { location.href = "/api/template"; };
  async function upload(f) {
    if (!f || !can("import")) return;
    const merge = importMode !== "replace";
    if (merge ? total && !confirm(tt("Add the new rows from \"{f}\" to the current list?\nRows whose IMEI already exists are skipped.", { f: f.name }))
              : !confirm(tt("REPLACE the whole client list with \"{f}\"? The old data will be removed.", { f: f.name }))) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      toast("warn", tt("Importing…"));
      const r = await api(`/api/upload?mode=${merge ? "merge" : "replace"}&normal=${$("#normal").value}&company=${$("#company").value}&rental=${$("#rental").value}&size=${$("#pageSize").value}`, { method: "POST", body: fd });
      selected.clear(); $("#q").value = ""; $("#dmin").value = $("#dmax").value = ""; $("#utype").value = "all";   // a leftover filter/search must not hide the new list
      document.querySelector("input[name=f][value=all]").checked = true;
      applyData(r.data);                                                      // show the new list right away (no refresh needed)
      if (r.mode === "merge") {
        const dup = r.duplicates ? tt(" Skipped {n} duplicate IMEI ({list}).", { n: r.duplicates.toLocaleString(), list: r.dup_imeis.join(", ") + (r.duplicates > r.dup_imeis.length ? "…" : "") }) : "";
        const noi = r.no_imei ? tt(" Skipped {n} row(s) without IMEI.", { n: r.no_imei.toLocaleString() }) : "";
        const warn = r.warnings && r.warnings.length ? tt(" But: {w}.", { w: r.warnings.join(" · ") }) : "";
        say(r.added && !warn ? "ok" : "warn", tt("Added {n} new row(s) of {total}.", { n: r.added.toLocaleString(), total: r.total.toLocaleString() }) + dup + noi + warn);
      } else if (r.warnings && r.warnings.length) say("warn", tt("Imported {n} row(s) from {f}, but: {w}. Fix them in Excel and import again.", { n: r.rows.toLocaleString(), f: r.file, w: r.warnings.join(" · ") }));
      else say("ok", tt("Imported {n} row(s) from {f}.", { n: r.rows.toLocaleString(), f: r.file }));
    } catch (e) { say("error", e.message); }
  }
  $("#file").onchange = (ev) => { upload(ev.target.files[0]); ev.target.value = ""; };
  // drag a file from your computer anywhere onto the page
  addEventListener("dragover", (ev) => ev.preventDefault());
  addEventListener("drop", (ev) => { ev.preventDefault(); upload(ev.dataTransfer.files[0]); });
  $("#all").onchange = (ev) => { document.querySelectorAll("#rows input").forEach((c) => { if (c.checked !== ev.target.checked) c.click(); }); };
  let qTimer;
  $("#q").addEventListener("input", () => { clearTimeout(qTimer); qTimer = setTimeout(() => { page = 1; load(); }, 300); });
  document.querySelectorAll("input[name=f],#normal,#company,#rental,#utype").forEach((e) => e.addEventListener("change", () => { page = 1; load(); }));
  let rTimer;
  for (const id of ["#dmin", "#dmax"]) $(id).addEventListener("input", () => { clearTimeout(rTimer); rTimer = setTimeout(() => { page = 1; load(); }, 350); });
  $("#rangeClear").onclick = () => { $("#dmin").value = $("#dmax").value = ""; page = 1; load(); };
  // "More" menu (Update expiry lives here)
  const closeMore = () => { $("#moreMenu").hidden = true; $("#btnMore").setAttribute("aria-expanded", "false"); };
  $("#btnMore").onclick = (ev) => { ev.stopPropagation(); const open = $("#moreMenu").hidden; $("#moreMenu").hidden = !open; $("#btnMore").setAttribute("aria-expanded", String(open)); };
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".more")) closeMore(); });
  $("#pageSize").onchange = () => { page = 1; load(); };
  $("#prev").onclick = () => { if (page > 1) { page--; load(); } };
  $("#next").onclick = () => { if (page < pages) { page++; load(); } };
  $("#selClear").onclick = () => { selected.clear(); render(); };
  $("#selAll").onclick = async () => {
    try { const d = await api("/api/ids?" + qs()); d.ids.forEach((i) => selected.add(i)); render(); say("ok", tt("{n} units selected.", { n: selected.size.toLocaleString() })); }
    catch (e) { say("error", e.message); }
  };

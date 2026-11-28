// Sort by column and the admin tools: update expiry, fill Username/ID.
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
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
    closeMore();
    if (!selected.size) return say("warn", tt("Select plates first (search a Name such as WL012, then 'Select all matching')."));
    $("#expInfo").textContent = tt("{n} plate(s) selected.", { n: selected.size.toLocaleString() }); $("#expDate").value = ""; showErr("#expErr"); $("#expDlg").showModal();
  };
  $("#expCancel").onclick = () => $("#expDlg").close();
  $("#expSave").onclick = async () => {
    if (!$("#expDate").value) return showErr("#expErr", tt("Choose the new expiry date."));
    try {
      const r = await api("/api/update_expiry", { method: "POST", body: JSON.stringify({ ids: [...selected], expiry_date: $("#expDate").value }) });
      $("#expDlg").close(); selected.clear(); say("ok", tt("New expiry date {d} saved on {n} plate(s).", { d: fmt($("#expDate").value), n: r.updated.toLocaleString() })); load();
    } catch (e) { showErr("#expErr", e.message); }
  };
  let nameMap = {};
  const FILL_HELP = tt("Type a Name. Every plate with this Name gets the Username/ID.");
  function fillList() {                          // the list shows only Names WITHOUT an ID (tick the box to also list the ones that have one)
    const all = $("#fillAll").checked, items = Object.values(nameMap).filter((n) => all || n.with_user < n.plates);
    $("#nameList").replaceChildren(...items.map((n) => { const o = document.createElement("option"); o.value = n.name;
      o.label = n.ids.length ? tt("ID: {ids}", { ids: n.ids.join(", ") }) : tt("{n} plate(s) · no ID", { n: n.plates }); return o; }));
    $("#fillCount").textContent = tt("{n} Name", { n: items.length.toLocaleString() });
  }
  $("#btnFill").onclick = async () => {
    $("#fillName").value = $("#q").value.trim(); $("#fillUser").value = ""; $("#fillAll").checked = false; showErr("#fillErr"); $("#fillInfo").textContent = FILL_HELP;
    try { const d = await api("/api/names"); nameMap = {}; d.names.forEach((n) => { nameMap[n.name.toLowerCase()] = n; }); fillList(); }
    catch (e) { /* the list is only a help */ }
    fillHint(); $("#fillDlg").showModal();
  };
  function fillHint() {
    const n = nameMap[$("#fillName").value.trim().toLowerCase()];
    if (!n) { $("#fillInfo").textContent = FILL_HELP; return; }
    $("#fillInfo").textContent = n.ids.length
      ? tt("Current ID: {ids} · {w}/{p} plate(s). Typing a new ID below will CHANGE it.", { ids: n.ids.join(", "), w: n.with_user, p: n.plates })
      : tt("{p} plate(s) have this Name, none has a Username/ID yet.", { p: n.plates });
    if (n.ids.length === 1 && !$("#fillUser").value) $("#fillUser").placeholder = tt("old: {id}", { id: n.ids[0] });
  }
  $("#fillName").addEventListener("input", fillHint);
  $("#fillAll").addEventListener("change", fillList);
  $("#fillCancel").onclick = () => $("#fillDlg").close();
  $("#fillSave").onclick = async () => {
    const name = $("#fillName").value.trim(), user = $("#fillUser").value.trim();
    if (!name || !user) return showErr("#fillErr", tt("Enter the Name and the Username/ID."));
    const n = nameMap[name.toLowerCase()];
    if (n && n.ids.length && !confirm(tt("{name} already has the Username/ID {ids}.\nChange it to {user} on all {p} plate(s)?", { name, ids: n.ids.join(", "), user, p: n.plates }))) return;
    try {
      const r = await api("/api/set_user", { method: "POST", body: JSON.stringify({ name, user }) });
      $("#fillDlg").close(); say("ok", tt("Username/ID {user} applied to {n} plate(s) named {name}.", { user, n: r.updated.toLocaleString(), name })); load();
    } catch (e) { showErr("#fillErr", e.message); }
  };

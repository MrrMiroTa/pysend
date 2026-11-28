// Admin users + permissions (Users tab).
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
  // ---------- admin users + permissions ----------
  const PERM_LABEL = Object.fromEntries(["report", "import", "send", "expiry", "fill_id", "export", "users"].map((k) => [k, tt("perm." + k)]));
  let dlgMode = null, dlgUser = null;
  async function loadUsers() {
    try {
      const d = await api("/api/users"), body = $("#uRows"); body.replaceChildren();
      for (const u of d.users) {
        const tr = document.createElement("tr");
        const c = el("div", "cell-user"); c.append(avatar(u.username), el("span", "", u.username + (u.me ? "  " + tt("(you)") : ""))); td(tr, c);
        td(tr, el("span", "badge " + (u.active ? "b-sent" : "b-failed"), u.active ? tt("Active") : tt("Disabled")));
        const tags = el("div", "perm-tags"); if (u.main) tags.append(el("span", "", tt("Main admin · all"))); else if (!u.permissions.length) tags.append(el("span", "", tt("— none —")));
        else u.permissions.forEach((p) => tags.append(el("span", "", PERM_LABEL[p] || p))); td(tr, tags);
        td(tr, u.created_at || "—", "hide-sm"); td(tr, u.last_login || "—", "hide-sm");
        const box = el("div", "row-btns"), act = (label, cls, fn) => { const b = el("button", "btn sm " + cls, label); b.type = "button"; b.onclick = fn; box.appendChild(b); };
        if (!u.main) act(tt("Permissions"), "", () => openDlg("perms", u));
        act(tt("Reset password"), "", () => openDlg("reset", u));
        if (!u.me) {
          act(u.active ? tt("Disable") : tt("Enable"), "", async () => { try { await api(`/api/users/${u.id}/active`, { method: "POST", body: JSON.stringify({ active: !u.active }) }); loadUsers(); } catch (e) { say("error", e.message); } });
          act(tt("Delete"), "danger", async () => { if (!confirm(tt("Delete user \"{u}\"?", { u: u.username }))) return; try { await api(`/api/users/${u.id}/delete`, { method: "POST", body: "{}" }); loadUsers(); } catch (e) { say("error", e.message); } });
        }
        td(tr, box); body.appendChild(tr);
      }
    } catch (e) { say("error", e.message); }
  }
  const permBoxes = () => [...document.querySelectorAll("#uPerms input[type=checkbox]")];
  function openDlg(mode, u) {
    dlgMode = mode; dlgUser = u; $("#uErr").hidden = true; $("#uPass").value = "";
    $("#uTitle").textContent = mode === "add" ? tt("Add user") : mode === "perms" ? tt("Permissions: {u}", { u: u.username }) : tt("Reset password: {u}", { u: u.username });
    $("#uName").value = u ? u.username : ""; $("#uName").disabled = mode !== "add";
    $("#uPassRow").hidden = mode === "perms"; $("#uPerms").hidden = mode === "reset";
    const have = new Set(mode === "perms" ? u.permissions : ["report", "import", "send", "expiry", "fill_id", "export"]);   // new users: everything except Admin
    permBoxes().forEach((b) => { b.checked = have.has(b.value); });
    $("#uDlg").showModal(); (mode === "add" ? $("#uName") : mode === "reset" ? $("#uPass") : $("#uSave")).focus();
  }
  async function saveDlg() {
    const perms = permBoxes().filter((b) => b.checked).map((b) => b.value);
    try {
      if (dlgMode === "add") await api("/api/users", { method: "POST", body: JSON.stringify({ username: $("#uName").value, password: $("#uPass").value, permissions: perms }) });
      else if (dlgMode === "perms") await api(`/api/users/${dlgUser.id}/permissions`, { method: "POST", body: JSON.stringify({ permissions: perms }) });
      else await api(`/api/users/${dlgUser.id}/password`, { method: "POST", body: JSON.stringify({ password: $("#uPass").value }) });
      $("#uDlg").close(); say("ok", tt(dlgMode === "add" ? "User created." : dlgMode === "perms" ? "Permissions saved." : "Password changed.")); loadUsers();
    } catch (e) { $("#uErr").textContent = e.message; $("#uErr").hidden = false; }
  }
  $("#uAdd").onclick = () => openDlg("add", null);
  $("#uSave").onclick = saveDlg; $("#uCancel").onclick = () => $("#uDlg").close();
  $("#uPass").addEventListener("keydown", (ev) => { if (ev.key === "Enter") saveDlg(); });

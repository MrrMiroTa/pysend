// Tabs (Dashboard / Report / Users) and start-up. Loaded last.
// Classic scripts share one scope; order in templates/index.html matters (main.js last).
  // ---------- tabs ----------
  let tab = "main";
  const VIEWS = { main: ["#viewMain", "#tabMain"], report: ["#viewReport", "#tabReport"], users: ["#viewUsers", "#tabUsers"] };
  function show(t) {
    tab = t;
    for (const [k, [v, b]] of Object.entries(VIEWS)) { $(v).hidden = k !== t; $(b).classList.toggle("on", k === t); }
    $("#pageTitle").textContent = TITLES[t][0]; $("#pageSub").textContent = TITLES[t][1];
    document.querySelector(".dock-btns").hidden = t !== "main";   // send buttons only on the Dashboard
    if (t === "report" && can("report")) { $("#viewRep").hidden = true; loadReport(); }
    if (t === "users" && can("users")) loadUsers();
    scrollTo({ top: 0 });
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
  $("#viewRep").onclick = () => { setRange("today", false); show("report"); };

  skeleton(); load(); poll(); setInterval(poll, 2000);

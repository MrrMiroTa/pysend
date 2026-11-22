(function () {
  var pw = document.getElementById("pw"), b = document.getElementById("pwToggle");
  if (!pw || !b) return;
  b.addEventListener("click", function () {
    var show = pw.type === "password";
    pw.type = show ? "text" : "password";
    b.setAttribute("aria-label", show ? "Hide password" : "Show password");
    b.querySelector("use").setAttribute("href", show ? "#i-eye-off" : "#i-eye");
  });
})();

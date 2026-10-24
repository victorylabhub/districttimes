(function () {
  // Keep the current section visible in the horizontally scrolling nav on phones.
  var cur = document.querySelector(".nav a[aria-current]");
  if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: "nearest", inline: "center" });

  // Site search over /search.json (no tracking, no third parties).
  var q = document.getElementById("q");
  if (!q) return;
  var out = document.getElementById("search-results"),
      status = document.getElementById("search-status"), data = null;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function run() {
    var v = q.value.trim().toLowerCase();
    if (!data) return;
    if (!v) { out.innerHTML = ""; status.textContent = data.length ? "" : "No articles have been published yet."; return; }
    var terms = v.split(/\s+/);
    var hits = data.filter(function (a) {
      var hay = (a.t + " " + a.d + " " + a.a + " " + a.s).toLowerCase();
      return terms.every(function (t) { return hay.indexOf(t) > -1; });
    });
    status.textContent = hits.length + (hits.length === 1 ? " result" : " results");
    out.innerHTML = hits.slice(0, 50).map(function (a) {
      return '<li><p class="kick">' + esc(a.s) + '</p><h2 class="hl"><a href="' + esc(a.u) + '">' + esc(a.t) +
        '</a></h2><p class="dek">' + esc(a.d) + '</p><p class="by">By <strong>' + esc(a.a) + "</strong> · " + esc(a.p) + "</p></li>";
    }).join("");
  }
  fetch("/search.json").then(function (r) { return r.json(); }).then(function (d) {
    data = d;
    var p = new URLSearchParams(location.search).get("q");
    if (p) q.value = p;
    run();
  }).catch(function () { status.textContent = "Search is unavailable right now."; });
  q.addEventListener("input", run);
  q.focus();
})();

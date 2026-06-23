// Theme toggle button. Initial class is set pre-paint by base.html
// to avoid FOUC; this file just wires the runtime toggle.

(function () {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
        var html = document.documentElement;
        var nowDark = html.classList.toggle("dark");
        try {
            localStorage.setItem("theme", nowDark ? "dark" : "light");
        } catch (e) { /* private mode: choice won't persist */ }
    });
})();

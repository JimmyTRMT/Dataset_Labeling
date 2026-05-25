// Theme toggle. The initial `dark` class is applied by an inline script
// in base.html (before paint, no FOUC). This file wires the toggle button
// once the page is interactive.

(function () {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
        var html = document.documentElement;
        var nowDark = html.classList.toggle("dark");
        try {
            localStorage.setItem("theme", nowDark ? "dark" : "light");
        } catch (e) { /* localStorage disabled - choice won't persist */ }
    });
})();

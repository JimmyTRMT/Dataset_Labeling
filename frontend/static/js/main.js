// Mobile nav toggle. Lives here so base.html stays JS-free.

(function () {
    var toggle = document.getElementById("mobile-nav-toggle");
    var panel = document.getElementById("mobile-nav-panel");
    var iconOpen = document.getElementById("mobile-nav-icon-open");
    var iconClose = document.getElementById("mobile-nav-icon-close");

    // Only signed-in users get the menu - bail otherwise.
    if (!toggle || !panel) return;

    function setOpen(isOpen) {
        panel.classList.toggle("hidden", !isOpen);
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        if (iconOpen && iconClose) {
            iconOpen.classList.toggle("hidden", isOpen);
            iconClose.classList.toggle("block", isOpen);
            iconClose.classList.toggle("hidden", !isOpen);
        }
    }

    toggle.addEventListener("click", function () {
        var isOpen = !panel.classList.contains("hidden");
        setOpen(!isOpen);
    });

    // Auto-close when crossing back to desktop, else the panel lingers
    // on top of the layout. 768px = Tailwind's `md` breakpoint.
    var mqDesktop = window.matchMedia("(min-width: 768px)");
    function handleViewportChange(event) {
        if (event.matches) setOpen(false);
    }
    if (typeof mqDesktop.addEventListener === "function") {
        mqDesktop.addEventListener("change", handleViewportChange);
    } else if (typeof mqDesktop.addListener === "function") {
        // Safari < 14.
        mqDesktop.addListener(handleViewportChange);
    }

    // Close on link tap so the next page loads clean.
    panel.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () { setOpen(false); });
    });
})();

// Flash toasts: auto-dismiss after 3s, close button removes immediately.

(function () {
    var toasts = document.querySelectorAll("[data-toast]");
    if (toasts.length === 0) return;

    function fadeAndRemove(toast) {
        toast.style.transition = "opacity 300ms";
        toast.style.opacity = "0";
        setTimeout(function () { toast.remove(); }, 300);
    }

    document.querySelectorAll("[data-toast-close]").forEach(function (button) {
        button.addEventListener("click", function () {
            var toast = button.closest("[data-toast]");
            if (toast) toast.remove();
        });
    });

    setTimeout(function () {
        toasts.forEach(fadeAndRemove);
    }, 3000);
})();

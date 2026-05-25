// Handles the flash toasts rendered by base.html:
//   * auto-dismiss every toast after 3s with a 300ms fade,
//   * close button per toast (data-toast-close) removes it immediately.
// Safe no-op when the page has no toast.

(function () {
    var toasts = document.querySelectorAll("[data-toast]");
    if (toasts.length === 0) return;

    function fadeAndRemove(toast) {
        toast.style.transition = "opacity 300ms";
        toast.style.opacity = "0";
        setTimeout(function () { toast.remove(); }, 300);
    }

    // Manual close: clicking the X removes the toast immediately.
    document.querySelectorAll("[data-toast-close]").forEach(function (button) {
        button.addEventListener("click", function () {
            var toast = button.closest("[data-toast]");
            if (toast) toast.remove();
        });
    });

    // Auto-dismiss after 3 seconds.
    setTimeout(function () {
        toasts.forEach(fadeAndRemove);
    }, 3000);
})();

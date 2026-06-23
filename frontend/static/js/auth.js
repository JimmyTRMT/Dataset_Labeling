// Auth pages: client-side hints only. WTForms does the real validation.

(function () {

    /* ---- live password-match check ---------------------------------- */

    function bindPasswordMatch(passwordId, confirmId, hintId) {
        var pw = document.getElementById(passwordId);
        var pwConfirm = document.getElementById(confirmId);
        var hint = document.getElementById(hintId);
        if (!pw || !pwConfirm) return;

        function check() {
            if (!hint) return;
            if (!pwConfirm.value) {
                hint.classList.add("hidden");
                pwConfirm.setCustomValidity("");
                return;
            }
            if (pw.value === pwConfirm.value) {
                hint.textContent = "Passwords match.";
                hint.className = "text-xs mt-1 text-blue-600 dark:text-blue-400";
                pwConfirm.setCustomValidity("");
            } else {
                hint.textContent = "Passwords do not match yet.";
                hint.className = "text-xs mt-1 text-amber-600 dark:text-amber-300";
                pwConfirm.setCustomValidity("Passwords do not match.");
            }
            hint.classList.remove("hidden");
        }

        pw.addEventListener("input", check);
        pwConfirm.addEventListener("input", check);
    }

    // Bind whichever pair is present (register vs reset use different ids).
    bindPasswordMatch("password", "password_confirm", "password-match-hint");
    bindPasswordMatch("new_password", "new_password_confirm", "password-match-hint");


    /* ---- English validation messages for required inputs ------------ */

    document.querySelectorAll("input[required], textarea[required]").forEach(function (input) {
        var fillMessage = "Please fill in this field.";
        input.addEventListener("invalid", function () {
            if (input.validity.valueMissing) {
                input.setCustomValidity(fillMessage);
            }
        });
        input.addEventListener("input", function () {
            // Only clear once the field is non-empty, else we wipe the
            // password-match hint set by bindPasswordMatch above.
            if (input.value && input.validity.valid) {
                input.setCustomValidity("");
            }
        });
    });

})();

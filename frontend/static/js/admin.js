// Confirm before deleting a user account.

(function () {
    document.querySelectorAll(".admin-delete-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var confirmed = confirm(
                "Delete this user account? Their annotations stay in the database."
            );
            if (!confirmed) event.preventDefault();
        });
    });
})();

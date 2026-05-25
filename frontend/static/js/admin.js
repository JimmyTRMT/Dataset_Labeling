// Admin user-management interactions: confirm before deleting a user
// account so an accidental click never wipes someone out silently.

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

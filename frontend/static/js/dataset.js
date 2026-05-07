// Dataset table: confirm before deleting an image so a stray click never
// destroys data silently.

document.querySelectorAll(".delete-image-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        const confirmed = confirm("Delete this image permanently?");
        if (!confirmed) {
            event.preventDefault();
        }
    });
});

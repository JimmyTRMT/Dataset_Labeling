// dataset.js contains JavaScript code that adds a confirmation dialog when a user attempts to delete an image from the dataset.
document.querySelectorAll(".delete-image-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        const confirmed = confirm("Delete this image permanently?");
        if (!confirmed) {
            event.preventDefault();
        }
    });
});

document.querySelectorAll(".delete-image-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        const confirmed = confirm("Delete this image permanently?");
        if (!confirmed) {
            event.preventDefault();
        }
    });
});

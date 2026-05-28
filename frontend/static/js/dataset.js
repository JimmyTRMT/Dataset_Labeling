// Dataset browser: per-section search, pagination, and delete confirm.
// Sections keep independent state so Fundus and WasteSorting paginate
// without stepping on each other.

(function () {

    function wireSection(section) {
        var body = section.querySelector("[data-dataset-body]");
        if (!body) return;

        var rows = Array.prototype.slice.call(body.querySelectorAll("[data-row]"));
        if (rows.length === 0) return;

        var searchInput = section.querySelector("[data-dataset-search]");
        var pageSizeSelect = section.querySelector("[data-dataset-page-size]");
        var prevButton = section.querySelector("[data-dataset-prev]");
        var nextButton = section.querySelector("[data-dataset-next]");
        var pageLabel = section.querySelector("[data-dataset-page-label]");
        var statusLabel = section.querySelector("[data-dataset-status]");

        var state = {
            query: "",
            pageSize: pageSizeSelect ? parseInt(pageSizeSelect.value, 10) || 10 : 10,
            page: 1,
        };

        function applyFiltersAndPagination() {
            var query = state.query.trim().toLowerCase();
            var filtered = rows.filter(function (row) {
                if (!query) return true;
                return (row.dataset.filename || "").indexOf(query) !== -1;
            });

            var pageCount = Math.max(1, Math.ceil(filtered.length / state.pageSize));
            if (state.page > pageCount) state.page = pageCount;

            var start = (state.page - 1) * state.pageSize;
            var end = start + state.pageSize;

            rows.forEach(function (row) { row.classList.add("hidden"); });
            filtered.slice(start, end).forEach(function (row) { row.classList.remove("hidden"); });

            if (pageLabel) {
                pageLabel.textContent = "Page " + state.page + " / " + pageCount;
            }
            if (prevButton) prevButton.disabled = state.page <= 1;
            if (nextButton) nextButton.disabled = state.page >= pageCount;
            if (statusLabel) {
                var visible = Math.min(filtered.length, end) - start;
                visible = Math.max(0, visible);
                statusLabel.textContent =
                    "Showing " + visible + " of " + filtered.length +
                    (query ? " match(es)" : " image(s)");
            }
        }

        if (searchInput) {
            searchInput.addEventListener("input", function (event) {
                state.query = event.target.value || "";
                state.page = 1;
                applyFiltersAndPagination();
            });
        }
        if (pageSizeSelect) {
            pageSizeSelect.addEventListener("change", function (event) {
                state.pageSize = parseInt(event.target.value, 10) || 10;
                state.page = 1;
                applyFiltersAndPagination();
            });
        }
        if (prevButton) {
            prevButton.addEventListener("click", function () {
                if (state.page > 1) {
                    state.page -= 1;
                    applyFiltersAndPagination();
                }
            });
        }
        if (nextButton) {
            nextButton.addEventListener("click", function () {
                state.page += 1;
                applyFiltersAndPagination();
            });
        }

        applyFiltersAndPagination();
    }

    document.querySelectorAll("[data-dataset-section]").forEach(wireSection);


    // Delete confirm on every form so a stray click can't wipe data.
    document.querySelectorAll(".delete-image-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var confirmed = confirm("Delete this image permanently?");
            if (!confirmed) event.preventDefault();
        });
    });

})();

// Labeling page interactions:
//   * progress-bar fill: width driven by a data-attribute,
//   * image viewer: custom zoom (wheel) + pan (drag) + rotate / flip / reset
//     via CSS transforms - no third-party library, exactly one <img> on screen,
//   * label cards: click or 1-9 to select, Enter to submit.

(function () {

    /* ---------- progress bar ----------------------------------------- */

    const progressFill = document.getElementById("progress-fill");
    if (progressFill) {
        const percent = parseFloat(progressFill.dataset.progress || "0");
        progressFill.style.width = Math.max(0, Math.min(100, percent)) + "%";
    }


    /* ---------- image viewer ----------------------------------------- */

    // State of the transform applied to the image. All five values combine
    // into one matrix that we re-apply on every change.
    const view = {
        zoom: 1,
        panX: 0,
        panY: 0,
        rotation: 0,
        flipX: 1,
        flipY: 1,
    };

    const ZOOM_MIN = 0.1;
    const ZOOM_MAX = 10;
    const ZOOM_STEP = 0.15;

    const frame = document.getElementById("image-viewer-frame");
    const image = document.getElementById("main-image");

    function applyTransform() {
        if (!image) return;
        // The trailing translate(-50%, -50%) keeps the image visually
        // centered before our pan/zoom transforms are added on top.
        image.style.transform =
            `translate(-50%, -50%) ` +
            `translate(${view.panX}px, ${view.panY}px) ` +
            `scale(${view.zoom * view.flipX}, ${view.zoom * view.flipY}) ` +
            `rotate(${view.rotation}deg)`;
    }

    function resetView() {
        view.zoom = 1;
        view.panX = 0;
        view.panY = 0;
        view.rotation = 0;
        view.flipX = 1;
        view.flipY = 1;
        applyTransform();
    }

    if (frame && image) {
        applyTransform();

        // Wheel zoom. preventDefault so the page does not scroll while
        // the user is sizing the image.
        frame.addEventListener("wheel", function (event) {
            event.preventDefault();
            const delta = event.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
            view.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, view.zoom + delta));
            applyTransform();
        }, { passive: false });

        // Click-and-drag panning. We track the starting pointer position
        // relative to the current pan so the image follows the cursor 1:1.
        let isDragging = false;
        let dragStartX = 0;
        let dragStartY = 0;

        image.addEventListener("mousedown", function (event) {
            event.preventDefault();
            isDragging = true;
            dragStartX = event.clientX - view.panX;
            dragStartY = event.clientY - view.panY;
            image.classList.add("is-dragging");
        });

        document.addEventListener("mousemove", function (event) {
            if (!isDragging) return;
            view.panX = event.clientX - dragStartX;
            view.panY = event.clientY - dragStartY;
            applyTransform();
        });

        document.addEventListener("mouseup", function () {
            if (!isDragging) return;
            isDragging = false;
            image.classList.remove("is-dragging");
        });

        // Don't let the browser drag the image as a file when the user
        // tries to pan it.
        image.addEventListener("dragstart", function (event) {
            event.preventDefault();
        });

        const bindClick = function (id, action) {
            const button = document.getElementById(id);
            if (button) button.addEventListener("click", action);
        };
        bindClick("rotate-left",     function () { view.rotation -= 90; applyTransform(); });
        bindClick("rotate-right",    function () { view.rotation += 90; applyTransform(); });
        bindClick("flip-horizontal", function () { view.flipX *= -1;    applyTransform(); });
        bindClick("flip-vertical",   function () { view.flipY *= -1;    applyTransform(); });
        bindClick("reset-view",      resetView);
    }


    /* ---------- label cards ------------------------------------------ */

    const labelButtons = document.querySelectorAll(".label-card");
    const selectedLabelInput = document.getElementById("selected-label-input");
    const saveButton = document.getElementById("save-label-btn");
    const labelForm = document.getElementById("label-form");

    let selectedButton = null;

    function selectLabel(button) {
        if (!button) return;
        if (selectedButton) {
            selectedButton.classList.remove("selected");
        }
        selectedButton = button;
        button.classList.add("selected");
        if (selectedLabelInput) {
            selectedLabelInput.value = button.dataset.label || "";
        }
        if (saveButton) {
            saveButton.disabled = false;
        }
    }

    labelButtons.forEach(function (button) {
        button.addEventListener("click", function () { selectLabel(button); });
    });

    if (labelForm) {
        labelForm.addEventListener("submit", function () {
            if (saveButton) {
                saveButton.classList.add("label-submit-pulse");
            }
        });
    }

    // Keyboard shortcuts: 1-9 picks the matching label, Enter submits when
    // a label is selected. Bail out if focus is in a form field so typing
    // in a text input would not steal the shortcuts.
    document.addEventListener("keydown", function (event) {
        const focusedTag = document.activeElement ? document.activeElement.tagName : "";
        if (["INPUT", "TEXTAREA", "SELECT"].includes(focusedTag)) {
            return;
        }

        const numberPressed = parseInt(event.key, 10);
        if (!isNaN(numberPressed) && numberPressed >= 1 && numberPressed <= 9) {
            if (numberPressed <= labelButtons.length) {
                selectLabel(labelButtons[numberPressed - 1]);
            }
            return;
        }

        if (event.key === "Enter" && selectedButton && labelForm && saveButton && !saveButton.disabled) {
            labelForm.submit();
        }
    });

})();

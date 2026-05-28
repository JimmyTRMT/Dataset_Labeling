// Annotation page: upload mode (dropzone + form) and label mode
// (viewer + label cards). Mode is detected from the DOM, not a flag.

(function () {

    /* ---- upload mode ------------------------------------------------ */

    var uploadForm = document.getElementById("annotation-upload-form");
    if (uploadForm) {
        var fileInput = document.getElementById("image");
        var dropzone = document.getElementById("dropzone");
        var selectedFileText = document.getElementById("selected-file-text");

        function updateSelectedFileText() {
            if (!fileInput || !selectedFileText) return;
            var files = fileInput.files;
            if (!files || files.length === 0) {
                selectedFileText.textContent = "or click to browse - no file selected";
            } else {
                selectedFileText.textContent = files[0].name;
            }
        }

        if (dropzone && fileInput) {
            dropzone.addEventListener("click", function () { fileInput.click(); });

            ["dragenter", "dragover"].forEach(function (eventName) {
                dropzone.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    dropzone.classList.add("ring-2", "ring-blue-500");
                });
            });
            ["dragleave", "drop"].forEach(function (eventName) {
                dropzone.addEventListener(eventName, function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    dropzone.classList.remove("ring-2", "ring-blue-500");
                });
            });
            dropzone.addEventListener("drop", function (event) {
                if (event.dataTransfer && event.dataTransfer.files.length) {
                    // One image per upload: drop the rest if the user drags several.
                    var dt = new DataTransfer();
                    dt.items.add(event.dataTransfer.files[0]);
                    fileInput.files = dt.files;
                    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });
            fileInput.addEventListener("change", updateSelectedFileText);
        }

        applyEnglishValidationToAll();
    }


    /* ---- label mode ------------------------------------------------- */

    var frame = document.getElementById("image-viewer-frame");
    var image = document.getElementById("main-image");
    var labelForm = document.getElementById("label-form");

    if (frame && image && labelForm) {
        wireImageViewer(frame, image);
        wireLabelCards(labelForm);
    }


    function wireImageViewer(frameEl, imageEl) {
        var view = { zoom: 1, panX: 0, panY: 0, rotation: 0, flipX: 1, flipY: 1 };
        var ZOOM_MIN = 0.1, ZOOM_MAX = 10, ZOOM_STEP = 0.15;

        function applyTransform() {
            imageEl.style.transform =
                "translate(-50%, -50%) " +
                "translate(" + view.panX + "px, " + view.panY + "px) " +
                "scale(" + (view.zoom * view.flipX) + ", " + (view.zoom * view.flipY) + ") " +
                "rotate(" + view.rotation + "deg)";
        }
        function resetView() {
            view.zoom = 1; view.panX = 0; view.panY = 0;
            view.rotation = 0; view.flipX = 1; view.flipY = 1;
            applyTransform();
        }
        applyTransform();

        frameEl.addEventListener("wheel", function (event) {
            event.preventDefault();
            var delta = event.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
            view.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, view.zoom + delta));
            applyTransform();
        }, { passive: false });

        // Pan + pinch-zoom via Pointer Events: one path for mouse, finger
        // and stylus. The frame carries `touch-none` so the browser does
        // not steal pinch / double-tap / pan gestures.
        const activePointers = new Map(); // pointerId -> { x, y }
        let panStartX = 0;
        let panStartY = 0;
        let pinchStartDistance = 0;
        let pinchStartZoom = 1;

        const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
        const pointerArray = () => Array.from(activePointers.values());

        const beginPan = (event) => {
            panStartX = event.clientX - view.panX;
            panStartY = event.clientY - view.panY;
            imageEl.classList.add("is-dragging");
        };

        const beginPinch = () => {
            const [a, b] = pointerArray();
            pinchStartDistance = distance(a, b) || 1;
            pinchStartZoom = view.zoom;
            imageEl.classList.remove("is-dragging");
        };

        frameEl.addEventListener("pointerdown", (event) => {
            // Keep right- and middle-click free for the browser.
            if (event.pointerType === "mouse" && event.button !== 0) return;

            event.preventDefault();
            // Pointer capture keeps move/up events flowing even when the
            // finger drifts off the frame mid-drag.
            frameEl.setPointerCapture(event.pointerId);
            activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

            if (activePointers.size === 1) {
                beginPan(event);
            } else if (activePointers.size === 2) {
                beginPinch();
            }
        });

        frameEl.addEventListener("pointermove", (event) => {
            if (!activePointers.has(event.pointerId)) return;
            activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

            if (activePointers.size === 1) {
                view.panX = event.clientX - panStartX;
                view.panY = event.clientY - panStartY;
                applyTransform();
            } else if (activePointers.size === 2) {
                const [a, b] = pointerArray();
                const ratio = distance(a, b) / pinchStartDistance;
                view.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, pinchStartZoom * ratio));
                applyTransform();
            }
        });

        const endPointer = (event) => {
            if (!activePointers.has(event.pointerId)) return;
            activePointers.delete(event.pointerId);

            if (activePointers.size === 1) {
                // 2 -> 1 finger: re-anchor pan on the remaining one to avoid a jump.
                const [remaining] = pointerArray();
                panStartX = remaining.x - view.panX;
                panStartY = remaining.y - view.panY;
                imageEl.classList.add("is-dragging");
            } else if (activePointers.size === 0) {
                imageEl.classList.remove("is-dragging");
            }
        };

        // Don't listen to pointerleave: pointer capture keeps events
        // flowing outside the frame, leave would kill the gesture early.
        frameEl.addEventListener("pointerup", endPointer);
        frameEl.addEventListener("pointercancel", endPointer);

        // Kill the native HTML5 drag-ghost on slow mouse pans.
        imageEl.addEventListener("dragstart", (event) => event.preventDefault());

        var bind = function (id, action) {
            var btn = document.getElementById(id);
            if (btn) btn.addEventListener("click", action);
        };
        bind("rotate-left",     function () { view.rotation -= 90; applyTransform(); });
        bind("rotate-right",    function () { view.rotation += 90; applyTransform(); });
        bind("flip-horizontal", function () { view.flipX *= -1; applyTransform(); });
        bind("flip-vertical",   function () { view.flipY *= -1; applyTransform(); });
        bind("reset-view",      resetView);
    }

    function wireLabelCards(form) {
        var cards = document.querySelectorAll(".label-card");
        var selectedInput = document.getElementById("selected-label-input");
        var saveButton = document.getElementById("save-label-btn");
        var current = null;

        function select(card) {
            if (!card) return;
            if (current) current.classList.remove("border-blue-500", "bg-blue-500/10");
            current = card;
            card.classList.add("border-blue-500", "bg-blue-500/10");
            if (selectedInput) selectedInput.value = card.dataset.label || "";
            if (saveButton) saveButton.disabled = false;
        }

        cards.forEach(function (card) {
            card.addEventListener("click", function () { select(card); });
        });

        document.addEventListener("keydown", function (event) {
            var focused = document.activeElement ? document.activeElement.tagName : "";
            if (["INPUT", "TEXTAREA", "SELECT"].indexOf(focused) !== -1) return;

            var n = parseInt(event.key, 10);
            if (!isNaN(n) && n >= 1 && n <= 9) {
                if (n <= cards.length) select(cards[n - 1]);
                return;
            }
            if (event.key === "Enter" && current && saveButton && !saveButton.disabled) {
                form.submit();
            }
        });
    }


    function applyEnglishValidationToAll() {
        document.querySelectorAll("input[required], textarea[required]").forEach(function (input) {
            var fileMessage = "Please choose one image file.";
            var fillMessage = "Please fill in this field.";

            input.addEventListener("invalid", function () {
                if (input.validity.valueMissing) {
                    input.setCustomValidity(input.type === "file" ? fileMessage : fillMessage);
                }
            });
            function clearGroupValidity() {
                input.setCustomValidity("");
                if (input.type === "radio" && input.name) {
                    document
                        .querySelectorAll('input[type="radio"][name="' + CSS.escape(input.name) + '"]')
                        .forEach(function (peer) { peer.setCustomValidity(""); });
                }
            }
            input.addEventListener("input", clearGroupValidity);
            input.addEventListener("change", clearGroupValidity);
        });
    }

})();

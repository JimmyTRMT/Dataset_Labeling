// Sync the progress bar width with server-computed percentage
const progressBar = document.getElementById("label-progress-bar");
if (progressBar) {
    const progressValue = parseInt(progressBar.dataset.progress || "0", 10);
    progressBar.style.width = progressValue + "%";
    const progressContainer = progressBar.closest(".progress");
    if (progressContainer) {
        progressContainer.setAttribute("aria-valuenow", String(progressValue));
    }
}

// Display flash messages as Bootstrap toasts
const flashToasts = document.querySelectorAll(".toast");
flashToasts.forEach(function (element) {
    const toast = new bootstrap.Toast(element);
    toast.show();
});

const labelForm = document.getElementById("label-form");
let labelFormSubmitting = false;
const selectedLabelInput = document.getElementById("selected-label-input");
const autoAdvanceToggle = document.getElementById("auto-advance-toggle");
const autoAdvanceInput = document.getElementById("auto-advance-input");

// Keep auto-advance
function updateAutoAdvanceState(value) {
    const normalized = value ? "1" : "0";
    const url = new URL(window.location.href);
    url.searchParams.set("auto_advance", normalized);
    if (autoAdvanceInput) {
        autoAdvanceInput.value = normalized;
    }
    window.history.replaceState({}, "", url.toString());
    localStorage.setItem("autoAdvance", normalized);
}

if (autoAdvanceToggle) {
    const storedAutoAdvance = localStorage.getItem("autoAdvance");
    if (storedAutoAdvance === "0" || storedAutoAdvance === "1") {
        const shouldEnable = storedAutoAdvance === "1";
        autoAdvanceToggle.checked = shouldEnable;
        updateAutoAdvanceState(shouldEnable);
    } else {
        updateAutoAdvanceState(autoAdvanceToggle.checked);
    }

    autoAdvanceToggle.addEventListener("change", function () {
        updateAutoAdvanceState(autoAdvanceToggle.checked);
    });
}

// Submit label choice with a short visual feedback pulse.
function submitWithVisualFeedback(button) {
    if (!labelForm || !button || labelFormSubmitting) {
        return;
    }

    const labelValue = button.dataset.label || "";
    if (selectedLabelInput) {
        selectedLabelInput.value = labelValue;
    }

    labelFormSubmitting = true;
    button.classList.add("label-submit-pulse");
    setTimeout(function () {
        if (autoAdvanceInput && autoAdvanceToggle) {
            autoAdvanceInput.value = autoAdvanceToggle.checked ? "1" : "0";
        }
        labelForm.submit();
    }, 140);
}

const dynamicLabelButtons = document.querySelectorAll(".dynamic-label-btn");
if (dynamicLabelButtons.length > 0) {
    dynamicLabelButtons.forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            submitWithVisualFeedback(btn);
        });
    });
}

// Keyboard shortcuts
document.addEventListener("keydown", function (event) {
    const focusedTagName = document.activeElement ? document.activeElement.tagName : "";
    if (["INPUT", "TEXTAREA", "SELECT"].includes(focusedTagName)) {
        return;
    }

    const key = event.key.toLowerCase();
    
    const num = parseInt(key, 10);
    if (!isNaN(num) && num >= 1 && num <= 9) {
        if (num <= dynamicLabelButtons.length) {
            dynamicLabelButtons[num - 1].click();
        }
    }
});

// Labeling page interactions: pick a label, sync to the hidden input,
// enable the Save button, and support 1-9 keyboard shortcuts.

const labelButtons = document.querySelectorAll(".label-option-btn");
const selectedLabelInput = document.getElementById("selected-label-input");
const saveButton = document.getElementById("save-label-btn");
const labelForm = document.getElementById("label-form");

let selectedButton = null;


// Marks one button as selected and pushes its label into the hidden input.
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
    button.addEventListener("click", function () {
        selectLabel(button);
    });
});

if (labelForm) {
    labelForm.addEventListener("submit", function () {
        if (saveButton) {
            saveButton.classList.add("label-submit-pulse");
        }
    });
}

// Keyboard shortcuts: 1-9 picks the matching label, Enter submits when a
// label is selected. We bail out when focus is in a form field so typing
// in a text box never triggers a label change.
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

    if (event.key === "Enter" && selectedButton && labelForm && !saveButton.disabled) {
        labelForm.submit();
    }
});

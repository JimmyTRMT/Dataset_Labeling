const labelButtons = document.querySelectorAll(".label-option-btn");
const selectedLabelInput = document.getElementById("selected-label-input");
const saveButton = document.getElementById("save-label-btn");
const labelForm = document.getElementById("label-form");

let selectedButton = null;
// selectLabel handles the logic for selecting a label button, updating the hidden input with the selected label, and enabling the save button.
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
// add event listeners to each label button
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
// add a keydown event listener to the document to handle keyboard shortcuts for label selection and form submission, while ignoring inputs when focus is on form fields.
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

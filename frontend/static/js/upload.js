const fileInput = document.getElementById("images");
const chooseFilesButton = document.getElementById("choose-files-btn");
const selectedFilesText = document.getElementById("selected-files-text");

// applyEnglishValidation adds custom validation messages in English for required input fields, including file inputs, and clears the message on user input.
function applyEnglishValidation(input) {
    const fileMessage = "Please choose at least one file.";
    const fillMessage = "Please fill in this field.";
    input.addEventListener("invalid", function () {
        if (input.validity.valueMissing) {
            input.setCustomValidity(input.type === "file" ? fileMessage : fillMessage);
        }
    });
    input.addEventListener("input", function () {
        input.setCustomValidity("");
    });
}

document.querySelectorAll("input[required], textarea[required]").forEach(applyEnglishValidation);

if (chooseFilesButton && fileInput) {
    chooseFilesButton.addEventListener("click", function () {
        fileInput.click();
    });
}
// add a change event listener to the file input to update the displayed text with the selected file names or count, providing feedback to the user about their selection.
if (fileInput && selectedFilesText) {
    fileInput.addEventListener("change", function () {
        const total = fileInput.files ? fileInput.files.length : 0;
        if (total === 0) {
            selectedFilesText.value = "No file selected";
        } else if (total === 1) {
            selectedFilesText.value = fileInput.files[0].name;
        } else {
            selectedFilesText.value = `${total} files selected`;
        }
    });
}

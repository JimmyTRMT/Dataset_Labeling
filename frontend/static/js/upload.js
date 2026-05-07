// Upload page: forward "Choose File" clicks to the hidden file input,
// show how many files are selected, and override the browser's native
// validation messages with English strings (the labels in label.html
// stay consistent regardless of browser locale).

const fileInput = document.getElementById("images");
const chooseFilesButton = document.getElementById("choose-files-btn");
const selectedFilesText = document.getElementById("selected-files-text");


// Wires English custom-validity messages onto a single required input.
// Radio buttons get extra care because picking one peer should clear the
// stale message left over on the others.
function applyEnglishValidation(input) {
    const fileMessage = "Please choose at least one file.";
    const fillMessage = "Please fill in this field.";

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
                .forEach(function (peer) {
                    peer.setCustomValidity("");
                });
        }
    }

    input.addEventListener("input", clearGroupValidity);
    input.addEventListener("change", clearGroupValidity);
}

document.querySelectorAll("input[required], textarea[required]").forEach(applyEnglishValidation);

if (chooseFilesButton && fileInput) {
    chooseFilesButton.addEventListener("click", function () {
        fileInput.click();
    });
}

// Keep the read-only text in sync with the hidden file input so the user
// can see what they picked.
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

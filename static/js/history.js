// Display flash messages as toasts.
document.querySelectorAll(".toast").forEach(function (element) {
    const toast = new bootstrap.Toast(element);
    toast.show();
});

// Force English validation messages regardless of the browser locale.
function applyEnglishValidationMessages(input) {
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
document.querySelectorAll("input[required], textarea[required]").forEach(applyEnglishValidationMessages);

const addSessionButtons = document.querySelectorAll(".add-session-btn");
const sessionInput = document.getElementById("session_name");
const fileInput = document.getElementById("images");
const chooseFilesButton = document.getElementById("choose-files-btn");
const selectedFilesText = document.getElementById("selected-files-text");
const uploadModeInput = document.getElementById("upload_mode");
const uploadModeHint = document.getElementById("upload-mode-hint");
const uploadForm = document.getElementById("session-upload-form");
const labelsContainer = document.getElementById("labels-container");
const addLabelBtn = document.getElementById("add-label-btn");

// Update the text that shows how many files are selected.
function updateSelectedFilesText() {
    if (!fileInput || !selectedFilesText) {
        return;
    }

    const totalFiles = fileInput.files ? fileInput.files.length : 0;
    if (totalFiles === 0) {
        selectedFilesText.value = "No file selected";
        return;
    }

    if (totalFiles === 1) {
        selectedFilesText.value = fileInput.files[0].name;
        return;
    }

    selectedFilesText.value = `${totalFiles} files selected`;
}

if (chooseFilesButton && fileInput) {
    chooseFilesButton.addEventListener("click", function () {
        fileInput.click();
    });
}

if (fileInput) {
    fileInput.addEventListener("change", updateSelectedFilesText);
}

// Manage dynamic labels addition
if (addLabelBtn && labelsContainer) {
    addLabelBtn.addEventListener("click", function () {
        const div = document.createElement("div");
        div.className = "input-group mb-2";
        
        const input = document.createElement("input");
        input.type = "text";
        input.name = "custom_labels";
        input.className = "form-control";
        input.placeholder = "New label";
        input.required = true;
        applyEnglishValidationMessages(input);

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn-outline-danger remove-label-btn";
        removeBtn.textContent = "X";
        removeBtn.onclick = function() { div.remove(); };
        
        div.appendChild(input);
        div.appendChild(removeBtn);
        labelsContainer.appendChild(div);
    });
}

// Manage dynamic labels removal for existing elements
if (labelsContainer) {
    labelsContainer.addEventListener("click", function(e) {
        if (e.target.classList.contains("remove-label-btn")) {
            e.target.closest(".input-group").remove();
        }
    });
}

// Fill session form with existing session metadata before appending images.
function switchToExistingSessionMode(buttonElement) {
    if (sessionInput) {
        sessionInput.value = buttonElement.dataset.sessionName || "";
    }
    
    if (labelsContainer && buttonElement.dataset.labels) {
        try {
            const labels = JSON.parse(buttonElement.dataset.labels);
            labelsContainer.innerHTML = "";
            labels.forEach((lbl) => {
                const div = document.createElement("div");
                div.className = "input-group mb-2";
                div.innerHTML = `<input name="custom_labels" type="text" class="form-control" value="${lbl}" required>`;
                labelsContainer.appendChild(div);
                const created = div.querySelector("input");
                if (created) {
                    applyEnglishValidationMessages(created);
                }
            });
        } catch (e) {
            console.error("Error parsing labels", e);
        }
    }
    if (uploadModeInput) {
        uploadModeInput.value = "existing";
    }
    if (uploadModeHint) {
        uploadModeHint.textContent = `Current mode: append to session "${buttonElement.dataset.sessionName || ""}"`;
    }
    if (uploadForm) {
        uploadForm.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (chooseFilesButton) {
        chooseFilesButton.focus();
    }
}

// Attach event listeners to "Add to Session" buttons
addSessionButtons.forEach(function (buttonElement) {
    buttonElement.addEventListener("click", function () {
        switchToExistingSessionMode(buttonElement);
    });
});

if (sessionInput) {
    sessionInput.addEventListener("input", function () {
        if (uploadModeInput) {
            uploadModeInput.value = "new";
        }
        if (uploadModeHint) {
            uploadModeHint.textContent = "Current mode: new session";
        }
    });
}

// Protect delete
function confirmDeleteSession(event) {
    const confirmed = confirm("Do you really want to delete this session and all its images?");
    if (!confirmed) {
        event.preventDefault();
    }
}

document.querySelectorAll(".delete-session-form").forEach(function (deleteSessionForm) {
    deleteSessionForm.addEventListener("submit", confirmDeleteSession);
});

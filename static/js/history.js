// Display flash messages as toasts.
document.querySelectorAll(".toast").forEach(function (element) {
    const toast = new bootstrap.Toast(element);
    toast.show();
});

const addSessionButtons = document.querySelectorAll(".add-session-btn");
const sessionInput = document.getElementById("session_name");
const labelOneInput = document.getElementById("label_option_1");
const labelTwoInput = document.getElementById("label_option_2");
const fileInput = document.getElementById("images");
const chooseFilesButton = document.getElementById("choose-files-btn");
const selectedFilesText = document.getElementById("selected-files-text");
const uploadModeInput = document.getElementById("upload_mode");
const uploadModeHint = document.getElementById("upload-mode-hint");
const uploadForm = document.getElementById("session-upload-form");

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

// Fill session form with existing session metadata before appending images.
function switchToExistingSessionMode(buttonElement) {
    if (sessionInput) {
        sessionInput.value = buttonElement.dataset.sessionName || "";
    }
    if (labelOneInput) {
        labelOneInput.value = buttonElement.dataset.labelOne || "";
    }
    if (labelTwoInput) {
        labelTwoInput.value = buttonElement.dataset.labelTwo || "";
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

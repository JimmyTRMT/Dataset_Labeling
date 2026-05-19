// Upload page interactions:
//   * dropzone: forward clicks AND drag-and-drop to the hidden file input,
//   * file-count label: keep the on-screen text in sync,
//   * validation: English messages that survive non-English browser locales.

const fileInput = document.getElementById("images");
const dropzone = document.getElementById("dropzone");
const selectedFilesText = document.getElementById("selected-files-text");


// Wires English custom-validity onto a single required input. Radio
// groups need extra care: picking one peer should clear stale messages
// left on the others (otherwise HTML5 keeps the group "invalid").
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


// Reflect the file count in the dropzone hint text. Triggered both by a
// regular click-to-browse and by drag-and-drop (we dispatch a `change`
// event manually after assigning the dropped FileList).
function updateSelectedFilesText() {
    if (!fileInput || !selectedFilesText) return;
    const total = fileInput.files ? fileInput.files.length : 0;
    if (total === 0) {
        selectedFilesText.textContent = "or click to browse - no file selected";
    } else if (total === 1) {
        selectedFilesText.textContent = fileInput.files[0].name;
    } else {
        selectedFilesText.textContent = total + " files selected";
    }
}

if (fileInput) {
    fileInput.addEventListener("change", updateSelectedFilesText);
}


// Drag-and-drop wiring. We swallow `dragover` so the browser does not
// open the file in a new tab, and toggle a visual class to give the
// user feedback that dropping right now would work.
if (dropzone && fileInput) {
    ["dragenter", "dragover"].forEach(function (eventName) {
        dropzone.addEventListener(eventName, function (event) {
            event.preventDefault();
            event.stopPropagation();
            dropzone.classList.add("is-dragover");
        });
    });

    ["dragleave", "drop"].forEach(function (eventName) {
        dropzone.addEventListener(eventName, function (event) {
            event.preventDefault();
            event.stopPropagation();
            dropzone.classList.remove("is-dragover");
        });
    });

    dropzone.addEventListener("drop", function (event) {
        if (event.dataTransfer && event.dataTransfer.files.length) {
            // Assign the dropped files to the hidden input so the form
            // submits them on POST as if the user had picked them.
            fileInput.files = event.dataTransfer.files;
            fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
    });
}

document.querySelectorAll("[data-image-dropzone]").forEach((dropzone) => {
    const form = dropzone.closest("form");
    const input = dropzone.querySelector('input[type="file"]');
    const preview = form.querySelector("[data-image-preview]");
    const placeholder = form.querySelector("[data-image-placeholder]");
    const removeCheckbox = form.querySelector('input[name="eliminar_imagen"]');
    let previewUrl = null;

    const showPreview = (file) => {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }

        if (!file) {
            if (preview.dataset.currentSrc && !removeCheckbox?.checked) {
                preview.src = preview.dataset.currentSrc;
                preview.alt = preview.dataset.currentAlt;
                preview.hidden = false;
                placeholder.hidden = true;
            } else {
                preview.hidden = true;
                preview.removeAttribute("src");
                placeholder.hidden = false;
            }
            return;
        }

        if (!file.type.startsWith("image/")) {
            input.setCustomValidity("Selecciona un archivo de imagen.");
            input.reportValidity();
            input.value = "";
            return;
        }

        input.setCustomValidity("");
        previewUrl = URL.createObjectURL(file);
        preview.src = previewUrl;
        preview.alt = `Vista previa: ${file.name}`;
        preview.hidden = false;
        placeholder.hidden = true;
        if (removeCheckbox) {
            removeCheckbox.checked = false;
        }
    };

    input.addEventListener("change", () => {
        showPreview(input.files[0]);
    });

    if (removeCheckbox) {
        removeCheckbox.addEventListener("change", () => {
            if (removeCheckbox.checked && !input.files.length) {
                preview.hidden = true;
                placeholder.hidden = false;
            } else if (!removeCheckbox.checked && !input.files.length) {
                if (preview.dataset.currentSrc) {
                    preview.src = preview.dataset.currentSrc;
                    preview.alt = preview.dataset.currentAlt;
                    preview.hidden = false;
                    placeholder.hidden = true;
                }
            }
        });
    }

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragging");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragging");
        });
    });

    dropzone.addEventListener("drop", (event) => {
        const [file] = event.dataTransfer.files;
        if (!file) {
            return;
        }

        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    form.addEventListener("submit", () => {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }
    });
});

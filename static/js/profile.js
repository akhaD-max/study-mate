(() => {
    const form = document.getElementById("profile-form");
    if (!form) return;

    const bio = document.getElementById("id_bio");
    const counter = document.getElementById("bio-counter");
    const dialog = document.getElementById("unsaved-dialog");
    const snapshot = () => JSON.stringify(
        Array.from(new FormData(form).entries())
            .filter(([name]) => name !== "csrfmiddlewaretoken")
    );
    const initial = snapshot();
    let submitting = false;
    let destination = null;
    const hasChanges = () => !submitting && (
        form.dataset.hasErrors === "true" || snapshot() !== initial
    );
    const updateCounter = () => {
        counter.textContent = `${Array.from(bio.value).length} / 1000 символов`;
    };
    bio.addEventListener("input", updateCounter);
    updateCounter();

    form.addEventListener("submit", () => { submitting = true; });
    window.addEventListener("beforeunload", (event) => {
        if (!hasChanges()) return;
        event.preventDefault();
        event.returnValue = "";
    });
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");
        if (!link || link.target === "_blank" || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || !hasChanges()) return;
        event.preventDefault();
        destination = link.href;
        dialog.showModal();
    });
    document.getElementById("keep-editing").addEventListener("click", () => dialog.close());
    document.getElementById("discard-changes").addEventListener("click", () => {
        submitting = true;
        window.location.assign(destination);
    });
})();

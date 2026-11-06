// StudyMate · мелкие улучшения формы отклика и строк списков.
// Делегирование событий, чтобы работать и после HTMX-обновлений.
document.addEventListener("input", (event) => {
    const textarea = event.target.closest("[data-counter-for]");
    if (!textarea) return;
    const counter = document.getElementById(textarea.getAttribute("data-counter-for"));
    if (counter) counter.textContent = String(textarea.value.length);
});

document.addEventListener("change", (event) => {
    const radio = event.target.closest(".pg-role-option input[type=\"radio\"]");
    if (!radio) return;
    const group = radio.closest(".pg-role-group");
    if (!group) return;
    group.querySelectorAll(".pg-role-option").forEach((option) => {
        const input = option.querySelector("input[type=\"radio\"]");
        option.classList.toggle("is-selected", Boolean(input && input.checked));
    });
});

document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-password-toggle]");
    if (!button) return;
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    button.textContent = visible ? "Скрыть" : "Показать";
    button.setAttribute("aria-label", visible ? "Скрыть пароль" : "Показать пароль");
    button.setAttribute("aria-pressed", String(visible));
});
document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id === "auth-form") {
        document.querySelector('#auth-form [aria-invalid="true"], #auth-title')?.focus();
    }
});
document.addEventListener("htmx:afterRequest", (event) => {
    const error = event.detail.elt.querySelector(".auth-network-error");
    if (error) error.hidden = !event.detail.failed;
});

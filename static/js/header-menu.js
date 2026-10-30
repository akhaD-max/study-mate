document.addEventListener("click", (event) => {
    document.querySelectorAll("details[data-user-menu][open]").forEach((menu) => {
        if (!menu.contains(event.target)) menu.open = false;
    });
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const menu = document.querySelector("details[data-user-menu][open]");
    if (!menu) return;
    menu.open = false;
    menu.querySelector("summary")?.focus();
});

(() => {
    const form = document.getElementById("profile-form");
    if (!form) return;

    const bio = document.getElementById("id_bio");
    const counter = document.getElementById("bio-counter");
    const dialog = document.getElementById("unsaved-dialog");
    const skillOptions = Array.from(form.querySelectorAll(".profile-skill-option"));
    const skillInputs = skillOptions.map((option) => option.querySelector("input"));
    const selectedSkills = document.getElementById("selected-skills");
    const skillCount = document.getElementById("skills-count");
    const skillFeedback = document.getElementById("skills-feedback");
    const skillSearch = document.getElementById("skill-search");
    const selected = () => skillInputs.filter((input) => input.checked);
    const skillName = (input) => input.closest("label").textContent.trim().split(" — ")[0];
    const renderSkills = () => {
        const skills = selected();
        selectedSkills.replaceChildren();
        selectedSkills.hidden = skills.length === 0;
        skillCount.textContent = `(${skills.length} / 15)`;
        for (const input of skills) {
            const tag = document.createElement("span");
            tag.className = "profile-tag";
            const name = document.createElement("span");
            name.textContent = skillName(input);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "profile-remove-skill";
            remove.setAttribute("aria-label", `Удалить навык: ${skillName(input)}`);
            remove.textContent = "×";
            remove.addEventListener("click", () => {
                input.checked = false;
                input.dispatchEvent(new Event("change", { bubbles: true }));
                document.querySelector("#skills-picker summary").focus();
            });
            tag.append(name, remove);
            selectedSkills.append(tag);
        }
    };
    for (const input of skillInputs) {
        input.addEventListener("change", () => {
            if (input.checked && selected().length > 15) {
                input.checked = false;
                skillFeedback.hidden = false;
                skillFeedback.textContent = "Можно выбрать не больше 15 навыков.";
            } else {
                skillFeedback.hidden = true;
            }
            renderSkills();
        });
    }
    skillSearch.parentElement.hidden = false;
    skillSearch.addEventListener("input", () => {
        const query = skillSearch.value.trim().toLocaleLowerCase("ru");
        for (const option of skillOptions) {
            option.hidden = !option.textContent.toLocaleLowerCase("ru").includes(query);
        }
        document.getElementById("skill-search-empty").hidden = skillOptions.some((option) => !option.hidden);
    });
    renderSkills();

    // Курс доступен только после выбора уровня образования, а сам уровень —
    // только для тех, кто ещё учится. Набор курсов зависит от уровня.
    const statusField = document.getElementById("id_education_status");
    const levelField = document.getElementById("id_education_level");
    const courseField = document.getElementById("id_course");
    const courseLimits = { bachelor: 4, specialist: 5, master: 2, postgraduate: 3 };
    const previous = { level: levelField ? levelField.value : "", course: courseField ? courseField.value : "" };
    const setDisabled = (field, disabled) => {
        field.disabled = disabled;
        const wrapper = field.closest(".profile-field");
        if (wrapper) wrapper.classList.toggle("is-disabled", disabled);
    };
    const renderCourses = () => {
        const limit = courseLimits[levelField.value] || 0;
        const keep = previous.course;
        courseField.replaceChildren(new Option("Выберите курс", ""));
        for (let number = 1; number <= limit; number += 1) {
            courseField.append(new Option(String(number), String(number)));
        }
        setDisabled(courseField, limit === 0);
        if (limit === 0) {
            courseField.value = "";
            return;
        }
        courseField.value = Number(keep) <= limit ? keep : "";
    };
    const renderEducation = () => {
        const studying = statusField.value === "studying";
        setDisabled(levelField, !studying);
        if (!studying) {
            previous.level = levelField.value === "" ? previous.level : levelField.value;
            levelField.value = "";
            previous.course = courseField.value || previous.course;
            renderCourses();
            return;
        }
        if (levelField.value) previous.level = levelField.value;
        renderCourses();
    };
    if (statusField && levelField && courseField) {
        statusField.addEventListener("change", renderEducation);
        levelField.addEventListener("change", () => {
            previous.course = "";
            renderCourses();
        });
        setDisabled(levelField, statusField.value !== "studying");
        renderCourses();
    }

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

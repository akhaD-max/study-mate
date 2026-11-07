// Делегированные события переживают замену #catalog-content через HTMX.
// Без JavaScript остаётся обычная GET-форма с кнопками Найти/Применить.
(() => {
    const isCatalog = (event) => event.detail.target?.id === 'catalog-content';
    let latestRequest = null;
    let failedPath = null;
    const showFailure = (event) => {
        if (event.detail.xhr !== latestRequest) return;
        // HTMX уже включил фильтры и page в URL. Текущая форма могла измениться.
        failedPath = event.detail.pathInfo.finalRequestPath;
        document.getElementById('catalog-request-error').hidden = false;
    };

    document.addEventListener('htmx:beforeRequest', (event) => {
        if (isCatalog(event)) latestRequest = event.detail.xhr;
    });
    document.addEventListener('click', (event) => {
        const button = event.target.closest('#catalog-retry');
        if (!button || !failedPath || button.disabled) return;
        // Кнопка вне формы: её новые значения не добавятся к сохранённому URL.
        htmx.ajax('GET', failedPath, {
            source: button, target: '#catalog-content', swap: 'outerHTML',
        }).catch(() => {
            // HTMX сообщает о сетевом сбое через sendError/timeout ниже.
        });
    });
    document.addEventListener('change', (event) => {
        if (event.target.id === 'catalog-sort') event.target.form.requestSubmit();
    });
    document.addEventListener('htmx:beforeSwap', (event) => {
        if (!isCatalog(event)) return;
        // Только для каталога разрешаем вставку HTML с ошибками формы.
        // Статус HTTP 400 сохраняется; 500 не заменяет прежние карточки.
        if (event.detail.xhr.status === 400) {
            event.detail.shouldSwap = true;
            event.detail.isError = false;
        }
        if (event.detail.xhr.status >= 500) {
            event.detail.shouldSwap = false;
            showFailure(event);
        }
    });
    for (const name of ['htmx:sendError', 'htmx:timeout', 'htmx:responseError']) {
        document.addEventListener(name, (event) => {
            if (isCatalog(event) && event.detail.xhr?.status !== 400) showFailure(event);
        });
    }
    document.addEventListener('htmx:afterSwap', (event) => {
        if (!isCatalog(event)) return;
        if (event.detail.xhr !== latestRequest) return;
        failedPath = null;
        document.getElementById('catalog-request-error').hidden = true;
        // При ошибке перемещаем фокус к сообщению для клавиатуры/диктора.
        const error = document.querySelector('#catalog-content [role="alert"]');
        if (error) {
            error.setAttribute('tabindex', '-1');
            error.focus();
        }
    });
})();

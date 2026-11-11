document.querySelectorAll("form[data-live-filter]").forEach((form) => {
    let submitTimer;
    let activeRequest;

    const status = form.querySelector("[data-live-status]");

    const buildUrl = () => {
        const url = new URL(form.action || window.location.href, window.location.origin);
        const params = new URLSearchParams(new FormData(form));
        params.delete("page");
        for (const [key, value] of params) {
            if (!value.trim()) {
                params.delete(key);
            }
        }
        url.search = params.toString();
        return url;
    };

    const updateResults = async (url, addHistoryEntry = false) => {
        activeRequest?.abort();
        activeRequest = new AbortController();
        const request = activeRequest;
        const targets = document.querySelectorAll("[data-live-results]");

        targets.forEach((target) => {
            target.setAttribute("aria-busy", "true");
        });
        if (status) {
            status.textContent = "Actualizando resultados…";
        }

        try {
            const response = await fetch(url, {
                signal: request.signal,
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!response.ok) {
                throw new Error(`La búsqueda respondió con el estado ${response.status}.`);
            }

            const documentResult = new DOMParser().parseFromString(
                await response.text(),
                "text/html",
            );
            for (const target of targets) {
                const replacement = documentResult.querySelector(
                    `[data-live-results="${target.dataset.liveResults}"]`,
                );
                if (!replacement) {
                    throw new Error("No se pudieron actualizar los resultados de esta página.");
                }
                target.innerHTML = replacement.innerHTML;
                target.removeAttribute("aria-busy");
            }

            if (addHistoryEntry) {
                window.history.pushState({}, "", url);
            } else {
                window.history.replaceState({}, "", url);
            }
            if (status) {
                status.textContent = "Resultados actualizados.";
            }
        } catch (error) {
            if (error.name !== "AbortError" && status) {
                status.textContent = "No se pudieron actualizar los resultados. Intenta nuevamente.";
                console.error(error);
            }
        } finally {
            if (activeRequest === request) {
                targets.forEach((target) => {
                    target.removeAttribute("aria-busy");
                });
            }
        }
    };

    const submitForm = () => {
        window.clearTimeout(submitTimer);
        updateResults(buildUrl());
    };

    form.addEventListener("input", (event) => {
        if (
            event.isComposing
            || !event.target.matches('input[type="search"], input[type="text"]')
        ) {
            return;
        }

        activeRequest?.abort();
        window.clearTimeout(submitTimer);
        submitTimer = window.setTimeout(submitForm, 500);
    });

    form.addEventListener("change", (event) => {
        if (event.target.matches("select, input[type='date']")) {
            submitForm();
        }
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        submitForm();
    });

    document.addEventListener("click", (event) => {
        const link = event.target.closest("[data-live-page]");
        if (!link || !document.querySelector("[data-live-results]")) {
            return;
        }
        event.preventDefault();
        window.clearTimeout(submitTimer);
        updateResults(new URL(link.href), true);
    });

    window.addEventListener("popstate", () => {
        const params = new URLSearchParams(window.location.search);
        for (const control of form.elements) {
            if (control.name && params.has(control.name)) {
                control.value = params.get(control.name);
            } else if (control.name && control.type !== "submit") {
                control.value = "";
            }
        }
        updateResults(new URL(window.location.href));
    });
});

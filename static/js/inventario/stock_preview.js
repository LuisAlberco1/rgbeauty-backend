(() => {
    document.querySelectorAll("[data-stock-preview]").forEach((preview) => {
        const form = preview.parentElement.querySelector("[data-stock-form]");
        const inventoryField = form.querySelector('[name="inventario"]');
        const productField = form.querySelector('[name="producto"]');
        const quantityField = form.querySelector('[name="cantidad"]');
        const mode = preview.dataset.mode;
        const currentStockElement = preview.querySelector("[data-current-stock]");
        const resultElement = preview.querySelector("[data-stock-result]");
        const statusElement = preview.querySelector("[data-stock-status]");
        const formatNumber = new Intl.NumberFormat("es-CL");
        let currentStock = null;
        let requestId = 0;
        let requestController = null;

        function setStatus(message, isError = false) {
            statusElement.textContent = message;
            statusElement.classList.toggle("is-error", isError);
        }

        function updatePreview() {
            resultElement.textContent = "";
            if (currentStock === null) {
                return;
            }

            const rawQuantity = quantityField.value.trim();
            if (!rawQuantity) {
                setStatus("Ingresa una cantidad para ver el resultado estimado.");
                return;
            }

            const quantity = Number(rawQuantity);
            if (!Number.isSafeInteger(quantity) || quantity < 0) {
                setStatus("Ingresa una cantidad válida.", true);
                return;
            }

            if (mode === "adjustment") {
                const difference = quantity - currentStock;
                resultElement.textContent =
                    `Stock final estimado: ${formatNumber.format(quantity)} unidades.`;
                if (difference > 0) {
                    setStatus(`El ajuste aumentará el stock en ${formatNumber.format(difference)} unidades.`);
                } else if (difference < 0) {
                    setStatus(`El ajuste disminuirá el stock en ${formatNumber.format(Math.abs(difference))} unidades.`);
                } else {
                    setStatus("El conteo coincide con el stock actual; no se registrará un movimiento.");
                }
                return;
            }

            if (quantity < 1) {
                setStatus("La cantidad de una entrada o salida debe ser mayor que cero.", true);
                return;
            }

            const movementType = form.querySelector('[name="tipo_movimiento"]')
                .selectedOptions[0]?.textContent.trim().toLowerCase();
            if (movementType === "salida" && quantity > currentStock) {
                resultElement.textContent = "No se puede completar: el stock quedaría negativo.";
                setStatus(`Disponible: ${formatNumber.format(currentStock)} unidades.`, true);
                return;
            }

            const newStock = movementType === "entrada"
                ? currentStock + quantity
                : currentStock - quantity;
            if (newStock > 2147483647) {
                resultElement.textContent = "No se puede completar: se supera el límite de stock.";
                setStatus(`Disponible: ${formatNumber.format(currentStock)} unidades.`, true);
                return;
            }

            resultElement.textContent =
                `Stock después del movimiento: ${formatNumber.format(newStock)} unidades.`;
            setStatus(`Stock actual: ${formatNumber.format(currentStock)} unidades.`);
        }

        async function loadCurrentStock() {
            requestId += 1;
            const thisRequestId = requestId;
            if (requestController) {
                requestController.abort();
            }
            currentStock = null;
            resultElement.textContent = "";

            if (!inventoryField.value || !productField.value) {
                currentStockElement.textContent =
                    "Selecciona un inventario y un producto para consultar sus existencias.";
                setStatus("");
                return;
            }

            currentStockElement.textContent = "Consultando stock actual...";
            setStatus("");
            requestController = new AbortController();
            const url = new URL(preview.dataset.stockUrl, window.location.origin);
            url.searchParams.set("inventario", inventoryField.value);
            url.searchParams.set("producto", productField.value);

            try {
                const response = await fetch(url, {
                    credentials: "same-origin",
                    signal: requestController.signal,
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "No se pudo consultar el stock.");
                }
                if (thisRequestId !== requestId) {
                    return;
                }

                currentStock = data.stock;
                currentStockElement.textContent =
                    `Stock actual: ${formatNumber.format(currentStock)} unidades.`;
                updatePreview();
            } catch (error) {
                if (error.name === "AbortError" || thisRequestId !== requestId) {
                    return;
                }
                currentStockElement.textContent = "Stock actual no disponible.";
                setStatus(error.message, true);
            }
        }

        inventoryField.addEventListener("change", loadCurrentStock);
        productField.addEventListener("change", loadCurrentStock);
        quantityField.addEventListener("input", updatePreview);
        const movementTypeField = form.querySelector('[name="tipo_movimiento"]');
        if (movementTypeField) {
            movementTypeField.addEventListener("change", updatePreview);
        }

        if (inventoryField.value && productField.value) {
            loadCurrentStock();
        }
    });
})();

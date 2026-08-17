/** @odoo-module **/

function initializeFanRegistrationForm() {
    const form = document.querySelector(".js_fc_fan_registration");
    if (!form || form.dataset.fcInitialized) {
        return;
    }
    form.dataset.fcInitialized = "true";

    const hint = form.querySelector(".js_fc_form_hint");
    const textInputs = form.querySelectorAll("input[type='text'], input[type='email'], input:not([type])");

    textInputs.forEach((input) => {
        input.addEventListener("blur", () => {
            input.value = input.value.trim();
        });
    });

    form.addEventListener("submit", () => {
        textInputs.forEach((input) => {
            input.value = input.value.trim();
        });
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton) {
            submitButton.disabled = true;
        }
        if (hint) {
            hint.classList.add("d-none");
        }
    });

    window.addEventListener("pageshow", () => {
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton) {
            submitButton.disabled = false;
        }
    });

    form.addEventListener("invalid", () => {
        if (hint) {
            hint.classList.remove("d-none");
        }
    }, true);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFanRegistrationForm);
} else {
    initializeFanRegistrationForm();
}

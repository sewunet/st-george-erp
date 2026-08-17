/** @odoo-module **/

function initializeClubLogin() {
    const page = document.querySelector(".sg-login-page");
    const passwordInput = document.querySelector(".sg-login-page input[name='password']");
    const toggle = document.querySelector(".sg-login-page .sg-password-toggle");
    const form = document.querySelector(".sg-login-page form.oe_login_form");

    if (!page) {
        return;
    }

    if (passwordInput && toggle && !toggle.dataset.sgInitialized) {
        toggle.dataset.sgInitialized = "true";
        toggle.addEventListener("click", () => {
            const isHidden = passwordInput.type === "password";
            passwordInput.type = isHidden ? "text" : "password";
            const label = isHidden ? toggle.dataset.hideLabel : toggle.dataset.showLabel;
            toggle.textContent = label;
            toggle.setAttribute("aria-label", label);
        });
    }

    if (form && !form.dataset.sgSubmitInitialized) {
        form.dataset.sgSubmitInitialized = "true";
        form.addEventListener("submit", () => {
            if (!form.checkValidity()) {
                return;
            }
            const submitButton = form.querySelector("button[type='submit']:not([name])");
            if (submitButton) {
                submitButton.disabled = true;
            }
        });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeClubLogin);
} else {
    initializeClubLogin();
}

window.addEventListener("pageshow", () => {
    const submitButton = document.querySelector(".sg-login-page form.oe_login_form button[type='submit']:not([name])");
    if (submitButton) {
        submitButton.disabled = false;
    }
});

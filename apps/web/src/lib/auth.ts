// Discord's login page sets a Cross-Origin-Opener-Policy that cuts the popup off from `window.opener`, so the popup
// reports back over a same-origin BroadcastChannel instead of `postMessage`
export const AUTH_CHANNEL = "square:auth";

/**
 * Opens Discord login in a centered popup. Returns `false` when the browser blocked it, so the caller can let the
 * link do a normal full-page login instead.
 */
export function openLoginPopup() {
    const width = 500;
    const height = 780;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const popup = window.open("/login?popup", "square-login", `popup,width=${width},height=${height},left=${left},top=${top}`);
    popup?.focus();
    return popup !== null;
}

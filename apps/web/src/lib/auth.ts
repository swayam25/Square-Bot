// Discord's login page cuts the popup off from `window.opener`, so it reports back over a BroadcastChannel
export const AUTH_CHANNEL = "square:auth";

export function openLoginPopup() {
    const width = 500;
    const height = 780;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const popup = window.open("/login?popup", "square-login", `popup,width=${width},height=${height},left=${left},top=${top}`);
    popup?.focus();
    return popup !== null;
}

// Discord's login page cuts the popup off from `window.opener`, so it reports back over a BroadcastChannel
export const AUTH_CHANNEL = "square:auth";

export function openPopup(url: string, name: string) {
    const width = 500;
    const height = 780;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const popup = window.open(url, name, `popup,width=${width},height=${height},left=${left},top=${top}`);
    popup?.focus();
    return popup;
}

export const openLoginPopup = () => openPopup("/login?popup", "square-login") !== null;

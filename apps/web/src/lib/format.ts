const full = new Intl.NumberFormat("en");
const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function formatCount(value: number) {
    return Math.abs(value) < 10_000 ? full.format(value) : compact.format(value);
}

export const plural = (count: number, word: string) => `${formatCount(count)} ${word}${count === 1 ? "" : "s"}`;

export function time(ms: number) {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(seconds / 3600);
    const rest = `${Math.floor((seconds % 3600) / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    return hours ? `${hours}:${rest.padStart(5, "0")}` : rest;
}

export const day = new Intl.DateTimeFormat("en", { dateStyle: "medium" });
export const dateTime = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });
export const monthYear = new Intl.DateTimeFormat("en", { month: "short", year: "numeric" });

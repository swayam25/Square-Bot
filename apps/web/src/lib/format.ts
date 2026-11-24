const full = new Intl.NumberFormat("en");
const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function formatCount(value: number) {
    return Math.abs(value) < 10_000 ? full.format(value) : compact.format(value);
}

export const plural = (count: number, word: string, words = `${word}s`) => `${formatCount(count)} ${count === 1 ? word : words}`;

export function time(ms: number) {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(seconds / 3600);
    const rest = `${Math.floor((seconds % 3600) / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    return hours ? `${hours}:${rest.padStart(5, "0")}` : rest;
}

export const day = new Intl.DateTimeFormat("en", { dateStyle: "medium" });
export const dateTime = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });
export const monthYear = new Intl.DateTimeFormat("en", { month: "short", year: "numeric" });

export function bytes(size: number) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
    return `${(size / 1024 / 1024).toFixed(1).replace(/\.0$/, "")} MB`;
}

const relativeFormat = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 365 * 24 * 60 * 60 * 1000],
    ["month", 30 * 24 * 60 * 60 * 1000],
    ["week", 7 * 24 * 60 * 60 * 1000],
    ["day", 24 * 60 * 60 * 1000],
    ["hour", 60 * 60 * 1000],
    ["minute", 60 * 1000],
];

export function relative(at: number, now: number) {
    const diff = at - now;
    for (const [unit, size] of UNITS) {
        if (Math.abs(diff) >= size) return relativeFormat.format(Math.round(diff / size), unit);
    }
    return relativeFormat.format(Math.round(diff / 1000), "second");
}

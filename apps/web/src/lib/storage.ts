// Storage throws in private windows or when site data is blocked. It only holds conveniences, so a failure is ignored
export function load(key: string) {
    try {
        return localStorage.getItem(key);
    } catch {
        return null;
    }
}

export function save(key: string, value: string) {
    try {
        localStorage.setItem(key, value);
    } catch {
        return;
    }
}

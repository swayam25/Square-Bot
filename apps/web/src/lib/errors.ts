export function errorMessage(err: unknown, fallback: string) {
    return (err as { body?: { message?: string } }).body?.message ?? fallback;
}

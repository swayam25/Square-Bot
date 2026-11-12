export const lyricsSync = $state({ offset: 0 });

export const SYNC_STEP_MS = 100;
export const SYNC_LIMIT_MS = 10_000;

export function nudgeSync(ms: number) {
    const next = Math.round((lyricsSync.offset + ms) / SYNC_STEP_MS) * SYNC_STEP_MS;
    lyricsSync.offset = Math.max(-SYNC_LIMIT_MS, Math.min(SYNC_LIMIT_MS, next));
}

export const syncLabel = (ms: number) => (ms === 0 ? "0.0s" : `${ms > 0 ? "+" : "−"}${(Math.abs(ms) / 1000).toFixed(1)}s`);

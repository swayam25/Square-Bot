import { refused } from "#lib/server/bot.ts";

const INLINE = new Set([
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/mp4",
    "audio/flac",
]);
const PASSED = ["content-length", "content-range", "accept-ranges"];
const ANSWER_WITHIN = 30_000;

type Fetched = { data?: unknown; error?: unknown; request?: Request; response?: Response };
type Fetch = (options: { headers: Record<string, string>; signal: AbortSignal }) => Promise<Fetched>;

/** Streams a stored file from the bot with range support. Pass a generated SDK call made with `parseAs: "stream"`. */
export async function streamFile(request: Request, fetch: Fetch): Promise<Response> {
    const range = request.headers.get("range");
    const answered = new AbortController();
    const timer = setTimeout(() => answered.abort(new DOMException("Square took too long to answer", "TimeoutError")), ANSWER_WITHIN);
    const result = await fetch({
        headers: range ? { range } : {},
        // Aborts the bot's stream when the viewer disconnects
        signal: AbortSignal.any([request.signal, answered.signal]),
    }).finally(() => clearTimeout(timer));

    if (result.response?.status === 416) {
        return new Response(null, { status: 416, headers: { "content-range": result.response.headers.get("content-range") ?? "" } });
    }
    const { data, response } = result;
    if (!(data instanceof ReadableStream) || !response) refused(result);

    const upstream = response.headers;
    const type = upstream.get("content-type")?.split(";")[0].trim().toLowerCase() ?? "";
    const inline = INLINE.has(type);
    const disposition = upstream.get("content-disposition") ?? "";
    const headers = new Headers({
        // Uploaded content never renders as a page: types outside INLINE only download
        "content-type": inline ? type : "application/octet-stream",
        "content-disposition": inline ? disposition || "inline" : disposition.startsWith("attachment") ? disposition : "attachment",
        "x-content-type-options": "nosniff",
        "content-security-policy": "default-src 'none'; sandbox",
        "cache-control": "private, max-age=86400, immutable",
    });
    for (const name of PASSED) {
        const value = upstream.get(name);
        if (value) headers.set(name, value);
    }
    return new Response(data, { status: response.status, headers });
}

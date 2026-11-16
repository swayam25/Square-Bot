import type { MessageSend } from "@square/api-client";
import { getContext, setContext } from "svelte";
import { SvelteMap } from "svelte/reactivity";

export const LIMITS = {
    components: 40,
    text: 4000,
    // Every gallery item, thumbnail and file in the message together
    media: 40,
    files: 10,
    filesBytes: 16 * 1024 * 1024,
    name: 80,
    label: 80,
    description: 1024,
    sectionTexts: 3,
    rowButtons: 5,
    galleryItems: 10,
    url: 512,
};

export type Media = { id: string; url: string; description: string; spoiler: boolean };
export type LinkButton = { id: string; kind: "button"; label: string; emoji: string; url: string; disabled: boolean };
export type Thumbnail = { id: string; kind: "thumbnail"; media: Media };
export type SectionText = { id: string; text: string };
export type Text = { id: string; kind: "text"; text: string };
export type Section = { id: string; kind: "section"; texts: SectionText[]; accessory: Thumbnail | LinkButton };
export type Gallery = { id: string; kind: "gallery"; items: Media[] };
export type FilePiece = { id: string; kind: "file"; url: string; spoiler: boolean };
export type Separator = { id: string; kind: "separator"; divider: boolean; large: boolean };
export type Row = { id: string; kind: "row"; buttons: LinkButton[] };
export type Piece = Text | Section | Gallery | FilePiece | Separator | Row;
export type Container = { id: string; kind: "container"; color: string | null; spoiler: boolean; children: Piece[] };
export type Block = Container | Piece;
export type Kind = Block["kind"];

export type Upload = { name: string; file: File; url: string };
export type Draft = { channelId: string | null; username: string; avatarUrl: string; blocks: Block[] };

export const ATTACHMENT = "attachment://";
const HTTPS = /^https:\/\/\S+$/;
const BUTTON_URL = /^(https?|discord):\/\/\S+$/;

export const uid = () => crypto.randomUUID();
export const media = (url = ""): Media => ({ id: uid(), url, description: "", spoiler: false });
export const linkButton = (): LinkButton => ({ id: uid(), kind: "button", label: "", emoji: "", url: "", disabled: false });

// `withMedia` false starts a section with a button, for when the message has no media slots left
export function create(kind: Kind, withMedia = true): Block {
    const id = uid();
    switch (kind) {
        case "container":
            return { id, kind, color: null, spoiler: false, children: [{ id: uid(), kind: "text", text: "" }] };
        case "text":
            return { id, kind, text: "" };
        case "section":
            return {
                id,
                kind,
                texts: [{ id: uid(), text: "" }],
                accessory: withMedia ? { id: uid(), kind: "thumbnail", media: media() } : linkButton(),
            };
        case "gallery":
            return { id, kind, items: [media()] };
        case "file":
            return { id, kind, url: "", spoiler: false };
        case "separator":
            return { id, kind, divider: true, large: false };
        case "row":
            return { id, kind, buttons: [linkButton()] };
    }
}

// New ids everywhere, so a copy never shares keys with the original
export function copy<T>(value: T): T {
    if (Array.isArray(value)) return value.map(copy) as T;
    if (value && typeof value === "object") {
        const entries = Object.entries(value).map(([key, item]) => [key, key === "id" ? uid() : copy(item)]);
        return Object.fromEntries(entries) as T;
    }
    return value;
}

// Counted like Discord: every nested component, but not the items inside a gallery
export function countOf(block: Block): number {
    switch (block.kind) {
        case "container":
            return 1 + block.children.reduce((sum, child) => sum + countOf(child), 0);
        case "section":
            return 2 + block.texts.length;
        case "row":
            return 1 + block.buttons.length;
        default:
            return 1;
    }
}

export function mediaOf(block: Block): number {
    switch (block.kind) {
        case "container":
            return block.children.reduce((sum, child) => sum + mediaOf(child), 0);
        case "gallery":
            return block.items.length;
        case "file":
            return 1;
        case "section":
            return block.accessory.kind === "thumbnail" ? 1 : 0;
        default:
            return 0;
    }
}

export const NO_ROOM = {
    components: `No room left: a message has up to ${LIMITS.components} components`,
    media: `No room left: a message shows up to ${LIMITS.media} pictures, videos and files`,
};

function* walk(blocks: Block[]): Generator<Block> {
    for (const block of blocks) {
        yield block;
        if (block.kind === "container") yield* block.children;
    }
}

export function textsOf(blocks: Block[]) {
    const texts: string[] = [];
    for (const block of walk(blocks)) {
        if (block.kind === "text") texts.push(block.text);
        if (block.kind === "section") texts.push(...block.texts.map((entry) => entry.text));
    }
    return texts;
}

export function mediaUrls(blocks: Block[]) {
    const urls: string[] = [];
    for (const block of walk(blocks)) {
        if (block.kind === "gallery") urls.push(...block.items.map((item) => item.url));
        if (block.kind === "file") urls.push(block.url);
        if (block.kind === "section" && block.accessory.kind === "thumbnail") urls.push(block.accessory.media.url);
    }
    return urls;
}

export const LABELS: Record<Kind, string> = {
    container: "Container",
    text: "Text",
    section: "Section",
    gallery: "Media gallery",
    file: "File",
    separator: "Separator",
    row: "Buttons",
};

export const validUrl = (url: string) => HTTPS.test(url.trim());
export const validButtonUrl = (url: string) => BUTTON_URL.test(url.trim()) && url.trim().length <= LIMITS.url;

function mediaProblem(url: string, uploads: Map<string, Upload>) {
    if (!url) return "has no picture or video";
    if (url.startsWith(ATTACHMENT)) return uploads.has(url.slice(ATTACHMENT.length)) ? null : "lost its upload, pick the file again";
    return validUrl(url) ? null : "needs an https link";
}

function buttonProblem(button: LinkButton) {
    if (!button.label.trim() && !button.emoji) return "needs a label or an emoji";
    if (!validButtonUrl(button.url)) return "needs a link";
    return null;
}

function pieceProblem(block: Block, uploads: Map<string, Upload>): string | null {
    switch (block.kind) {
        case "container":
            return block.children.length ? null : "is empty";
        case "text":
            return block.text.trim() ? null : "is empty";
        case "section": {
            if (block.texts.some((entry) => !entry.text.trim())) return "has an empty text";
            const accessory = block.accessory;
            const problem = accessory.kind === "button" ? buttonProblem(accessory) : mediaProblem(accessory.media.url, uploads);
            return problem && (accessory.kind === "button" ? `button ${problem}` : `thumbnail ${problem}`);
        }
        case "gallery": {
            const index = block.items.findIndex((item) => mediaProblem(item.url, uploads));
            return index === -1 ? null : `item ${index + 1} ${mediaProblem(block.items[index]!.url, uploads)}`;
        }
        case "file":
            if (!block.url) return "has no file";
            return uploads.has(block.url.slice(ATTACHMENT.length)) ? null : "lost its upload, pick the file again";
        case "row": {
            const index = block.buttons.findIndex((button) => buttonProblem(button));
            return index === -1 ? null : `button ${index + 1} ${buttonProblem(block.buttons[index]!)}`;
        }
        case "separator":
            return null;
    }
}

// Names the first thing that blocks sending, in words a person can find in the editor
export function problemOf(blocks: Block[], uploads: Map<string, Upload>): string | null {
    for (const [index, block] of blocks.entries()) {
        const name = `${LABELS[block.kind]} ${index + 1}`;
        const own = pieceProblem(block, uploads);
        if (own) return `${name} ${own}`;
        if (block.kind !== "container") continue;
        for (const [childIndex, child] of block.children.entries()) {
            const problem = pieceProblem(child, uploads);
            if (problem) return `${LABELS[child.kind]} ${childIndex + 1} in ${name} ${problem}`;
        }
    }
    return null;
}

const strip = (media: Media) => ({
    url: media.url.trim(),
    description: media.description.trim() || null,
    spoiler: media.spoiler,
});

const button = (button: LinkButton) => ({
    kind: "button" as const,
    url: button.url.trim(),
    label: button.label.trim() || null,
    emoji: button.emoji || null,
    disabled: button.disabled,
});

function piece(block: Piece): MessageSend["components"][number] {
    switch (block.kind) {
        case "text":
            return { kind: "text", text: block.text };
        case "section":
            return {
                kind: "section",
                texts: block.texts.map((entry) => entry.text),
                accessory: block.accessory.kind === "button" ? button(block.accessory) : { kind: "thumbnail", media: strip(block.accessory.media) },
            };
        case "gallery":
            return { kind: "gallery", items: block.items.map(strip) };
        case "file":
            return { kind: "file", url: block.url, spoiler: block.spoiler };
        case "separator":
            return { kind: "separator", divider: block.divider, large: block.large };
        case "row":
            return { kind: "row", buttons: block.buttons.map(button) };
    }
}

export function toComponents(blocks: Block[]): MessageSend["components"] {
    return blocks.map((block) =>
        block.kind === "container"
            ? { kind: "container", color: block.color, spoiler: block.spoiler, children: block.children.map((child) => piece(child) as never) }
            : piece(block),
    );
}

// Discord matches `attachment://` names exactly, so names keep to the safe set and never repeat
export function uploadName(file: File, taken: { has: (name: string) => boolean }) {
    const dot = file.name.lastIndexOf(".");
    const ext =
        dot > 0
            ? file.name
                  .slice(dot)
                  .replace(/[^\w.-]/g, "")
                  .slice(0, 10)
            : "";
    const stem = (dot > 0 ? file.name.slice(0, dot) : file.name).replace(/[^\w.-]/g, "_").slice(0, 80) || "file";
    let name = `${stem}${ext}`;
    for (let n = 2; taken.has(name); n += 1) name = `${stem}-${n}${ext}`;
    return name;
}

export const isVideo = (name: string, type?: string) => (type ? type.startsWith("video/") : /\.(mp4|webm|mov|m4v)(\?|$)/i.test(name));

export class Uploads {
    #files = new SvelteMap<string, Upload>();

    get map() {
        return this.#files;
    }

    add(file: File) {
        const name = uploadName(file, this.#files);
        this.#files.set(name, { name, file, url: URL.createObjectURL(file) });
        return `${ATTACHMENT}${name}`;
    }

    of(url: string) {
        return url.startsWith(ATTACHMENT) ? this.#files.get(url.slice(ATTACHMENT.length)) : undefined;
    }

    clear() {
        for (const upload of this.#files.values()) URL.revokeObjectURL(upload.url);
        this.#files.clear();
    }
}

export type ComposerContext = {
    uploads: Uploads;
    guild: { id: string; name: string; iconUrl: string | null };
    // Room left before the 40 component limit
    readonly room: number;
    // Room left before the 40 media limit
    readonly mediaRoom: number;
    // Why a block can't be added or copied right now, or null when it fits
    full: (block: Block) => string | null;
    // Every container in the message, so a piece can move into one
    readonly containers: Container[];
    move: (piece: Piece, to: Container | null) => void;
    // Checks the size, keeps the file and returns its attachment:// link, or null when it was refused
    upload: (file: File) => string | null;
};

const KEY = Symbol("composer");
export const setComposer = (context: ComposerContext) => setContext(KEY, context);
export const getComposer = () => getContext<ComposerContext>(KEY);

export function readFile(file: File) {
    return new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
    });
}

export const MEDIA_TYPES = "image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm,video/quicktime";

export function pickFiles(accept: string | undefined, multiple = false) {
    return new Promise<File[]>((resolve) => {
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = multiple;
        if (accept) input.accept = accept;
        input.addEventListener("change", () => resolve([...(input.files ?? [])]));
        input.addEventListener("cancel", () => resolve([]));
        input.click();
    });
}

export function accepts(file: File, accept: string | undefined) {
    return !accept || accept.split(",").includes(file.type);
}

export function parseEmoji(token: string): { name: string; id?: string; animated?: boolean } {
    const custom = /^<(a?):(\w+):(\d{17,20})>$/.exec(token);
    return custom ? { name: custom[2]!, id: custom[3]!, animated: custom[1] === "a" } : { name: token };
}

import type { Kind } from "#lib/composer.svelte.ts";
import type { Component } from "svelte";
import MaterialSymbolsAttachFileRounded from "~icons/material-symbols/attach-file-rounded";
import MaterialSymbolsCropSquareRounded from "~icons/material-symbols/crop-square-rounded";
import MaterialSymbolsHorizontalRuleRounded from "~icons/material-symbols/horizontal-rule-rounded";
import MaterialSymbolsNotesRounded from "~icons/material-symbols/notes-rounded";
import MaterialSymbolsPhotoLibraryRounded from "~icons/material-symbols/photo-library-rounded";
import MaterialSymbolsSmartButtonRounded from "~icons/material-symbols/smart-button-rounded";
import MaterialSymbolsVerticalSplitRounded from "~icons/material-symbols/vertical-split-rounded";

export const KINDS: Record<Kind, { icon: Component; hint: string }> = {
    container: { icon: MaterialSymbolsCropSquareRounded, hint: "A box with an accent color that holds other pieces" },
    text: { icon: MaterialSymbolsNotesRounded, hint: "Markdown, mentions and emojis" },
    section: { icon: MaterialSymbolsVerticalSplitRounded, hint: "Up to 3 texts with a thumbnail or button beside them" },
    gallery: { icon: MaterialSymbolsPhotoLibraryRounded, hint: "Up to 10 pictures or videos" },
    file: { icon: MaterialSymbolsAttachFileRounded, hint: "An uploaded file people can download" },
    separator: { icon: MaterialSymbolsHorizontalRuleRounded, hint: "Space between pieces, with or without a line" },
    row: { icon: MaterialSymbolsSmartButtonRounded, hint: "Up to 5 link buttons, like a server invite" },
};

export const TOP_KINDS: Kind[] = ["container", "text", "section", "gallery", "file", "separator", "row"];
export const INNER_KINDS: Kind[] = ["text", "section", "gallery", "file", "separator", "row"];

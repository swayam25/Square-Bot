// Discord serves an animated avatar or icon as a GIF and its first frame as WebP. The `a_` hash marks the animated ones
const ANIMATED = /^(https:\/\/cdn\.discordapp\.com\/.+\/a_[0-9a-f]+)\.(?:gif|webp|png|jpe?g)(\?.*)?$/;

export function frames(src: string | null | undefined) {
    const found = ANIMATED.exec(src ?? "");
    return found ? { still: `${found[1]}.webp${found[2] ?? ""}`, moving: `${found[1]}.gif${found[2] ?? ""}` } : null;
}

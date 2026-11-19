export function blobPath(lobes: number, depth: number, cx = 50, cy = 50, size = 50) {
    const steps = Math.max(64, lobes * 16);
    const points: string[] = [];
    for (let step = 0; step < steps; step++) {
        const angle = (step / steps) * Math.PI * 2;
        const radius = (size * (1 + depth * Math.cos(lobes * angle))) / (1 + depth);
        points.push(`${(cx + radius * Math.sin(angle)).toFixed(1)} ${(cy - radius * Math.cos(angle)).toFixed(1)}`);
    }
    return `M${points.join("L")}Z`;
}

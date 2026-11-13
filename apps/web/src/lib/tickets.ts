import type { Tone } from "#lib/components/ui/Chip.svelte";
import type { TicketEntry } from "@square/api-client";

type Status = TicketEntry["status"];

export const statusTone: Record<Status, Tone> = { open: "success", closed: "muted", deleted: "danger" };
export const statusName: Record<Status, string> = { open: "Open", closed: "Closed", deleted: "Deleted" };

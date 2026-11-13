import { forGuild, read } from "#lib/server/bot.ts";
import { command, query } from "$app/server";
import * as sdk from "@square/api-client";
import { z } from "zod";

const snowflake = z.string().regex(/^\d{17,20}$/);
const ticket = z.object({ guild: snowflake, number: z.int().min(1).max(10_000_000) });
const path = ({ guild, number }: z.infer<typeof ticket>) => ({ ...forGuild(guild), path: { guild_id: guild, number } });

export const ticketList = query(
    z.object({
        guild: snowflake,
        status: z.enum(["open", "closed", "deleted", "all"]),
        q: z.string().max(100),
        order: z.enum(["asc", "desc"]),
        page: z.int().min(1).max(100_000),
    }),
    ({ guild, q, ...params }) => read(sdk.listTickets({ ...forGuild(guild), query: { ...params, ...(q.trim() && { q: q.trim() }) } })),
);

export const ticketDetail = query(ticket, (args) => read(sdk.getTicket(path(args))));
export const closeTicket = command(ticket, (args) => read(sdk.closeTicket(path(args))));
export const reopenTicket = command(ticket, (args) => read(sdk.reopenTicket(path(args))));
export const deleteTicket = command(ticket, (args) => read(sdk.deleteTicket(path(args))));
export const purgeTicket = command(ticket, (args) => read(sdk.purgeTicket(path(args))));
export const purgeDeletedTickets = command(snowflake, (guild) => read(sdk.purgeDeletedTickets(forGuild(guild))));
export const ticketTranscript = query(ticket, (args) => read(sdk.ticketTranscript(path(args))));

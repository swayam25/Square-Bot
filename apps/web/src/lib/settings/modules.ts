import type { ModuleSettings } from "@square/api-client";
import type { Component } from "svelte";
import MaterialSymbolsConfirmationNumberRounded from "~icons/material-symbols/confirmation-number-rounded";
import MaterialSymbolsDescriptionRounded from "~icons/material-symbols/description-rounded";
import MaterialSymbolsPersonAddRounded from "~icons/material-symbols/person-add-rounded";

export type ModuleKey = keyof ModuleSettings;

export const MODULES: { key: ModuleKey; label: string; description: string; path: string; icon: Component }[] = [
    {
        key: "invites",
        label: "Invites",
        description: "Track who invited whom, with invite cards and a leaderboard.",
        path: "invites",
        icon: MaterialSymbolsPersonAddRounded,
    },
    {
        key: "tickets",
        label: "Tickets",
        description: "Private help channels between members and your staff.",
        path: "tickets",
        icon: MaterialSymbolsConfirmationNumberRounded,
    },
    {
        key: "logs",
        label: "Logs",
        description: "Post what happens in the server to the channels you pick.",
        path: "logs",
        icon: MaterialSymbolsDescriptionRounded,
    },
];

export const MODULE_OFF = 409;

export const moduleAt = (path: string) => MODULES.find((module) => module.path === path);

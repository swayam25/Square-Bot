import { MODULE_OFF, moduleAt } from "#lib/modules.ts";
import { forGuild, read } from "#lib/server/bot.ts";
import * as sdk from "@square/api-client";
import { error } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ parent, route }) => {
    const { guild } = await parent();
    if (!guild.canManage) error(403, "Changing Square's settings here needs the Manage Server permission.");

    const module = moduleAt(route.id.split("/").at(-1) ?? "");
    if (module && !(await read(sdk.getModuleSettings(forGuild(guild.id))))[module.key]) {
        error(MODULE_OFF, `${module.label} is turned off in ${guild.name}. Turn it on from the Overview page to use it.`);
    }
};

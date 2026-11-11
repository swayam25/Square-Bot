import { error } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ parent }) => {
    const { guild } = await parent();
    if (!guild.canManage) error(403, "Changing Square's settings here needs the Manage Server permission.");
};

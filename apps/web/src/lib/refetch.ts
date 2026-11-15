import type { RemoteQuery } from "$app/server";

// NOTE: Kit doesn't refetch queries on navigation yet, so callers refresh from `afterNavigate`.
// Replace with `refreshOnNavigation` once https://github.com/sveltejs/kit/pull/15775 lands.
export async function refetch(current: () => RemoteQuery<unknown> | null | undefined) {
    const query = current();
    if (query?.ready) await query.refresh().catch(() => {});
}

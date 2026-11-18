<script lang="ts">
    import SettingGroup from "#lib/components/dashboard/SettingGroup.svelte";
    import SettingRow from "#lib/components/dashboard/SettingRow.svelte";
    import { permissionName, type Permission } from "#lib/permissions.ts";
    import MaterialSymbolsLockPersonRounded from "~icons/material-symbols/lock-person-rounded";

    let {
        label,
        permission,
        kept = "Your settings are kept and start working once it has it.",
    }: { label: string; permission: Permission; kept?: string } = $props();
</script>

<SettingGroup>
    <SettingRow
        {label}
        description="Square needs the {permissionName(permission)} permission. {kept} Sync the server after giving it."
        icon={MaterialSymbolsLockPersonRounded}
        tone="danger"
    />
</SettingGroup>

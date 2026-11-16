<script lang="ts">
    import Button from "#lib/components/ui/Button.svelte";
    import FieldError from "#lib/components/ui/FieldError.svelte";
    import Popup from "#lib/components/ui/Popup.svelte";
    import { passPress } from "#lib/components/ui/press.ts";
    import ScrollRow from "#lib/components/ui/ScrollRow.svelte";
    import { field, focusRing } from "#lib/components/ui/styles.ts";
    import Tooltip from "#lib/components/ui/Tooltip.svelte";
    import { DateInput } from "@ark-ui/svelte/date-input";
    import { DatePicker, type DateValue } from "@ark-ui/svelte/date-picker";
    import { CalendarDateTime, toCalendarDate } from "@internationalized/date";
    import type { ClassValue } from "svelte/elements";
    import MaterialSymbolsCalendarMonthRounded from "~icons/material-symbols/calendar-month-rounded";
    import MaterialSymbolsChevronLeftRounded from "~icons/material-symbols/chevron-left-rounded";
    import MaterialSymbolsChevronRightRounded from "~icons/material-symbols/chevron-right-rounded";
    import MaterialSymbolsScheduleRounded from "~icons/material-symbols/schedule-rounded";

    export type Preset = { label: string; at: () => number };

    let {
        value = $bindable(null),
        title,
        min,
        max,
        presets = [],
        error,
        disabled = false,
        class: className,
    }: {
        value?: number | null;
        title: string;
        min?: number;
        max?: number;
        presets?: Preset[];
        error?: string | null;
        disabled?: boolean;
        class?: ClassValue;
    } = $props();

    const errorId = $props.id();
    let open = $state(false);
    let box = $state<HTMLElement>();
    let timeBox = $state<HTMLElement>();
    const firstSegment = (node: HTMLElement | undefined) =>
        [...(node?.querySelectorAll<HTMLElement>("[data-part=segment][data-editable]") ?? [])].find((segment) => segment.offsetParent);

    const toDateTime = (ms: number) => {
        const date = new Date(ms);
        return new CalendarDateTime(date.getFullYear(), date.getMonth() + 1, date.getDate(), date.getHours(), date.getMinutes());
    };
    const toMs = (date: DateValue, hour: number, minute: number) => new Date(date.year, date.month - 1, date.day, hour, minute).getTime();
    const nextHour = () => {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours() + 1).getTime();
    };

    const current = $derived(value === null ? null : toDateTime(value));
    const minDay = $derived(min === undefined ? undefined : toCalendarDate(toDateTime(min)));
    const maxDay = $derived(max === undefined ? undefined : toCalendarDate(toDateTime(max)));

    function setFull(next: DateValue[]) {
        const date = next[0];
        value = date && "hour" in date ? toMs(date, date.hour, date.minute) : null;
    }

    function setDay(next: DateValue | undefined) {
        if (!next) return;
        const base = current ?? toDateTime(nextHour());
        value = toMs(next, base.hour, base.minute);
    }

    const segment = [
        "rounded-md px-0.5 whitespace-pre tabular-nums outline-none data-[type=literal]:px-0",
        "data-placeholder-shown:text-gray-400 focus:bg-accent focus:text-cyan-950",
    ];
    const cell = [
        "flex cursor-pointer items-center justify-center rounded-full text-sm font-medium tabular-nums transition-colors outline-none",
        "hover:bg-white/10 focus-visible:ring-2 focus-visible:ring-accent/60",
        "data-outside-range:text-gray-500 data-today:inset-ring-2 data-today:inset-ring-white/20",
        "data-selected:bg-accent data-selected:font-semibold data-selected:text-cyan-950 data-selected:inset-ring-0",
        "data-disabled:pointer-events-none data-disabled:opacity-30",
    ];
    const navButton = [
        "ripple flex size-10 items-center justify-center rounded-full text-gray-400 hover:bg-white/10 hover:text-gray-100 disabled:opacity-30 md:size-8 [&>svg]:size-5",
        focusRing,
    ];
    const viewTrigger = ["cursor-pointer rounded-full px-3 py-1 text-sm font-semibold hover:bg-white/10", focusRing];
</script>

<div class={["group/field relative", className]}>
    <div class={[field, "pr-1.5 md:pr-1"]} bind:this={box} {@attach passPress(() => firstSegment(box))}>
        <DateInput.Root
            value={current ? [current] : []}
            onValueChange={(details) => setFull(details.value)}
            defaultPlaceholderValue={toDateTime(nextHour())}
            granularity="minute"
            hourCycle={12}
            locale="en"
            invalid={!!error}
            {disabled}
            class="min-w-0 flex-1"
        >
            <DateInput.Control>
                <DateInput.SegmentGroup
                    aria-label={title}
                    aria-describedby={error ? errorId : undefined}
                    class="flex min-w-0 [scrollbar-width:none] items-center overflow-x-auto"
                >
                    <DateInput.SegmentContext>
                        {#snippet render(part)}<DateInput.Segment segment={part} class={segment} />{/snippet}
                    </DateInput.SegmentContext>
                </DateInput.SegmentGroup>
            </DateInput.Control>
        </DateInput.Root>

        <Tooltip content="Pick from a calendar">
            <Popup
                bind:open
                {title}
                {disabled}
                placement="bottom-end"
                contentClass="w-80"
                triggerClass={[
                    "ripple flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full text-gray-400 hover:bg-white/10 hover:text-gray-100 disabled:pointer-events-none disabled:opacity-50 md:size-8 [&>svg]:size-5",
                    focusRing,
                ]}
            >
                {#snippet trigger()}<MaterialSymbolsCalendarMonthRounded />{/snippet}

                <div class="flex flex-col gap-4 p-2 md:p-0">
                    {#if presets.length}
                        <ScrollRow class="gap-2">
                            {#each presets as preset (preset.label)}
                                <Button size="xs" onclick={() => (value = preset.at())}>{preset.label}</Button>
                            {/each}
                        </ScrollRow>
                    {/if}

                    <DatePicker.Root
                        inline
                        locale="en"
                        min={minDay}
                        max={maxDay}
                        value={current ? [toCalendarDate(current)] : []}
                        onValueChange={(details) => setDay(details.value[0])}
                        class="flex justify-center"
                    >
                        <DatePicker.View view="day" class="flex flex-col gap-2">
                            <DatePicker.Context>
                                {#snippet render(picker)}
                                    <DatePicker.ViewControl class="flex items-center justify-between gap-2">
                                        <Tooltip content="Previous month">
                                            <DatePicker.PrevTrigger class={navButton}><MaterialSymbolsChevronLeftRounded /></DatePicker.PrevTrigger>
                                        </Tooltip>
                                        <DatePicker.ViewTrigger class={viewTrigger}><DatePicker.RangeText /></DatePicker.ViewTrigger>
                                        <Tooltip content="Next month">
                                            <DatePicker.NextTrigger class={navButton}><MaterialSymbolsChevronRightRounded /></DatePicker.NextTrigger>
                                        </Tooltip>
                                    </DatePicker.ViewControl>
                                    <DatePicker.Table class="border-separate border-spacing-0">
                                        <DatePicker.TableHead>
                                            <DatePicker.TableRow>
                                                {#each picker().weekDays as weekDay (weekDay.long)}
                                                    <DatePicker.TableHeader class="h-8 text-xs font-medium text-gray-400"
                                                        >{weekDay.narrow}</DatePicker.TableHeader
                                                    >
                                                {/each}
                                            </DatePicker.TableRow>
                                        </DatePicker.TableHead>
                                        <DatePicker.TableBody>
                                            {#each picker().weeks as week, index (index)}
                                                <DatePicker.TableRow>
                                                    {#each week as date (date.toString())}
                                                        <DatePicker.TableCell value={date}>
                                                            <DatePicker.TableCellTrigger class={[cell, "size-10"]}
                                                                >{date.day}</DatePicker.TableCellTrigger
                                                            >
                                                        </DatePicker.TableCell>
                                                    {/each}
                                                </DatePicker.TableRow>
                                            {/each}
                                        </DatePicker.TableBody>
                                    </DatePicker.Table>
                                {/snippet}
                            </DatePicker.Context>
                        </DatePicker.View>

                        <DatePicker.View view="month" class="flex w-full flex-col gap-2">
                            <DatePicker.Context>
                                {#snippet render(picker)}
                                    <DatePicker.ViewControl class="flex items-center justify-between gap-2">
                                        <Tooltip content="Previous year">
                                            <DatePicker.PrevTrigger class={navButton}><MaterialSymbolsChevronLeftRounded /></DatePicker.PrevTrigger>
                                        </Tooltip>
                                        <DatePicker.ViewTrigger class={viewTrigger}><DatePicker.RangeText /></DatePicker.ViewTrigger>
                                        <Tooltip content="Next year">
                                            <DatePicker.NextTrigger class={navButton}><MaterialSymbolsChevronRightRounded /></DatePicker.NextTrigger>
                                        </Tooltip>
                                    </DatePicker.ViewControl>
                                    <DatePicker.Table class="w-full border-separate border-spacing-1">
                                        <DatePicker.TableBody>
                                            {#each picker().getMonthsGrid({ columns: 3, format: "short" }) as months, index (index)}
                                                <DatePicker.TableRow>
                                                    {#each months as month (month.value)}
                                                        <DatePicker.TableCell value={month.value}>
                                                            <DatePicker.TableCellTrigger class={[cell, "h-12 w-full"]}
                                                                >{month.label}</DatePicker.TableCellTrigger
                                                            >
                                                        </DatePicker.TableCell>
                                                    {/each}
                                                </DatePicker.TableRow>
                                            {/each}
                                        </DatePicker.TableBody>
                                    </DatePicker.Table>
                                {/snippet}
                            </DatePicker.Context>
                        </DatePicker.View>

                        <DatePicker.View view="year" class="flex w-full flex-col gap-2">
                            <DatePicker.Context>
                                {#snippet render(picker)}
                                    <DatePicker.ViewControl class="flex items-center justify-between gap-2">
                                        <Tooltip content="Previous years">
                                            <DatePicker.PrevTrigger class={navButton}><MaterialSymbolsChevronLeftRounded /></DatePicker.PrevTrigger>
                                        </Tooltip>
                                        <span class="text-sm font-semibold">{picker().getDecade().start} – {picker().getDecade().end}</span>
                                        <Tooltip content="Next years">
                                            <DatePicker.NextTrigger class={navButton}><MaterialSymbolsChevronRightRounded /></DatePicker.NextTrigger>
                                        </Tooltip>
                                    </DatePicker.ViewControl>
                                    <DatePicker.Table class="w-full border-separate border-spacing-1">
                                        <DatePicker.TableBody>
                                            {#each picker().getYearsGrid({ columns: 3 }) as years, index (index)}
                                                <DatePicker.TableRow>
                                                    {#each years as year (year.value)}
                                                        <DatePicker.TableCell value={year.value}>
                                                            <DatePicker.TableCellTrigger class={[cell, "h-12 w-full"]}
                                                                >{year.label}</DatePicker.TableCellTrigger
                                                            >
                                                        </DatePicker.TableCell>
                                                    {/each}
                                                </DatePicker.TableRow>
                                            {/each}
                                        </DatePicker.TableBody>
                                    </DatePicker.Table>
                                {/snippet}
                            </DatePicker.Context>
                        </DatePicker.View>
                    </DatePicker.Root>

                    <div class="flex items-center gap-2">
                        <div class={[field, "flex-1"]} bind:this={timeBox} {@attach passPress(() => firstSegment(timeBox))}>
                            <MaterialSymbolsScheduleRounded />
                            <DateInput.Root
                                value={[current ?? toDateTime(nextHour())]}
                                onValueChange={(details) => setFull(details.value)}
                                granularity="minute"
                                hourCycle={12}
                                locale="en"
                                class={["min-w-0 flex-1", !current && "text-gray-400"]}
                            >
                                <DateInput.Control>
                                    <DateInput.SegmentGroup aria-label="Time" class="flex items-center">
                                        <DateInput.Context>
                                            {#snippet render(input)}
                                                {@const parts = input().getSegments()}
                                                {@const firstTime = parts.findIndex((part) => part.type === "hour")}
                                                <!-- Ark finds the focused segment by its position among all of them, so the date parts stay in the DOM, just hidden -->
                                                {#each parts as part, index (index)}
                                                    <DateInput.Segment segment={part} class={[segment, index < firstTime && "hidden"]} />
                                                {/each}
                                            {/snippet}
                                        </DateInput.Context>
                                    </DateInput.SegmentGroup>
                                </DateInput.Control>
                            </DateInput.Root>
                        </div>
                        <Button variant="primary" onclick={() => (open = false)}>Done</Button>
                    </div>
                </div>
            </Popup>
        </Tooltip>
    </div>
    <FieldError id={errorId} {error} />
</div>

export const focusRing = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export const field = [
    "flex h-12 w-full min-w-0 items-center gap-2 rounded-full bg-gray-800 px-4 text-sm md:h-10 [&>svg]:size-4 [&>svg]:shrink-0 [&>svg]:text-gray-400",
    "ring-0 ring-accent/60 ring-inset transition-[background-color,box-shadow] duration-200 ease-out",
    "hover:bg-gray-700 focus-within:ring-2",
    "has-[[aria-invalid=true]]:bg-red-400/10 has-[[aria-invalid=true]]:ring-red-400/40",
    "has-[input:disabled]:pointer-events-none has-[input:disabled]:opacity-50",
];

export const fieldText = "w-full min-w-0 flex-1 bg-transparent outline-none placeholder:text-gray-400";

export const menuPanel =
    "max-h-72 origin-(--transform-origin) overflow-y-auto overscroll-contain rounded-2xl bg-gray-800 p-2 shadow-2xl shadow-black/50 outline-none data-[state=closed]:animate-pop-out data-[state=open]:animate-pop-in";

export const menuItem =
    "flex h-10 cursor-pointer items-center gap-4 rounded-xl px-4 text-sm font-medium data-disabled:cursor-default data-disabled:opacity-50 data-highlighted:bg-white/10 data-[state=checked]:text-accent";

export const sheetItem =
    "ripple flex h-12 shrink-0 items-center gap-4 rounded-2xl px-4 text-left text-sm font-medium hover:bg-white/10 disabled:opacity-50 aria-selected:bg-accent/10 aria-selected:text-accent";

export const menuRow =
    "ripple flex h-10 w-full items-center gap-4 rounded-xl px-4 text-sm font-medium hover:bg-white/10 [&>svg]:size-5 [&>svg]:shrink-0 [&>svg]:text-gray-400";

export const menuNote = "px-4 py-2 text-sm text-gray-400";

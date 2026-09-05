import { BookOpenCheck } from "lucide-react"

import { cn } from "@/lib/utils"

export function WorkspaceBrand({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-16 items-center gap-3 border-b px-4",
        className,
      )}
    >
      <span className="relative flex size-9 shrink-0 items-center justify-center rounded-xl bg-[var(--ink)] text-white shadow-[0_5px_14px_rgba(25,25,29,0.18)]">
        <BookOpenCheck className="size-4" aria-hidden="true" />
        <span
          className="absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-[var(--shell)] bg-[var(--success)]"
          aria-hidden="true"
        />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm leading-4 font-semibold tracking-[-0.015em]">
          Course Digital Twin
        </span>
        <span className="mt-0.5 block truncate text-xs leading-4 text-muted-foreground">
          Governed autonomy
        </span>
      </span>
    </div>
  )
}

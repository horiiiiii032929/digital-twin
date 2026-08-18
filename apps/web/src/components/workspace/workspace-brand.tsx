import { BookOpenCheck } from "lucide-react"

import { cn } from "@/lib/utils"

export function WorkspaceBrand({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-14 items-center gap-2.5 border-b px-4",
        className,
      )}
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-[10px] bg-[var(--ink)] text-white">
        <BookOpenCheck className="size-4" aria-hidden="true" />
      </span>
      <span className="min-w-0 text-sm leading-4 font-semibold tracking-[-0.015em]">
        Course Digital Twin
      </span>
    </div>
  )
}

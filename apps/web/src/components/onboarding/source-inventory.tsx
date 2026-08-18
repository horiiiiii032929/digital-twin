import { useState } from "react"
import { Ban, Check, FileText, Loader2, ShieldAlert, Upload } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Alert, AlertDescription } from "@/components/ui/alert"
import type {
  SourceInventoryItem,
  SourceLabel,
  SourcePermissionStatus,
} from "@/lib/api/types"
import { cn } from "@/lib/utils"

type SourceInventoryProps = {
  items: SourceInventoryItem[]
  blockers: string[]
  isAdding: boolean
  updatingSourceId: string | null
  onAddSource: (item: {
    name: string
    mime_type: string
    size_bytes: number
    notes?: string
  }) => Promise<boolean>
  onUpdateSource: (
    sourceId: string,
    updates: Partial<
      Pick<
        SourceInventoryItem,
        | "permission_status"
        | "source_label"
        | "excluded"
        | "sensitive"
        | "notes"
      >
    >,
  ) => Promise<void>
}

const SOURCE_LABELS: SourceLabel[] = [
  "course-approved",
  "professor-approved-external",
  "system-suggested-trusted",
  "unapproved-external",
]

export function SourceInventory({
  items,
  blockers,
  isAdding,
  updatingSourceId,
  onAddSource,
  onUpdateSource,
}: SourceInventoryProps) {
  const [selectedFile, setSelectedFile] = useState<{
    name: string
    mime_type: string
    size_bytes: number
  } | null>(null)
  const [notes, setNotes] = useState("")
  const hasApprovedSource = items.some(
    (item) => item.permission_status === "approved" && !item.excluded,
  )
  const sourceStatus =
    blockers.length === 0 && hasApprovedSource
      ? "clear"
      : blockers.length > 0
        ? `${blockers.length} blocker${blockers.length === 1 ? "" : "s"}`
        : "needs source"

  const addSelected = async () => {
    if (!selectedFile || isAdding) {
      return
    }

    const added = await onAddSource({
      ...selectedFile,
      notes: notes.trim(),
    })
    if (!added) {
      return
    }
    setSelectedFile(null)
    setNotes("")
  }

  return (
    <section className="p-5 text-card-foreground sm:p-6" aria-labelledby="source-inventory-title">
      <div className="flex items-start justify-between gap-3 border-b pb-5">
        <div>
          <h3 id="source-inventory-title" className="text-lg font-semibold tracking-[-0.02em]">
            Sources
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Add course-material metadata and decide what the tutor may use.
          </p>
        </div>
        <Badge
          variant="outline"
          className={cn(
            "status-badge",
            sourceStatus === "clear"
              ? "status-badge-success"
              : "status-badge-warning",
          )}
        >
          {sourceStatus}
        </Badge>
      </div>

      <div className="flex flex-col gap-5 pt-5">
        <div className="rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--shell)] p-4">
          <label className="grid gap-2 text-sm font-medium">
            <span className="flex items-center gap-2">
              <Upload className="size-4 text-[var(--accent-strong)]" />
              Add course file metadata
            </span>
            <input
              type="file"
              className="min-h-10 text-sm text-muted-foreground file:mr-3 file:min-h-9 file:rounded-lg file:border file:border-border file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-[var(--ink)] hover:file:border-[var(--border-strong)]"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (!file) {
                  setSelectedFile(null)
                  return
                }
                setSelectedFile({
                  name: file.name,
                  mime_type: file.type || "application/octet-stream",
                  size_bytes: file.size,
                })
              }}
            />
            <span className="text-xs font-normal leading-5 text-muted-foreground">
              Only file name, type, size, and permission notes are saved. File
              contents are not uploaded or parsed.
            </span>
          </label>

          {selectedFile && (
            <div className="mt-4 grid gap-3 border-t pt-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{selectedFile.name}</Badge>
                <span className="text-xs text-muted-foreground">
                  {formatBytes(selectedFile.size_bytes)}
                </span>
              </div>
              <input
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Optional permission notes"
                aria-label="Source permission notes"
                className="h-10 rounded-lg border bg-white px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25"
              />
              <Button
                type="button"
                size="sm"
                onClick={() => void addSelected()}
                disabled={isAdding}
              >
                {isAdding ? (
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                ) : (
                  <Upload data-icon="inline-start" />
                )}
                Add metadata
              </Button>
            </div>
          )}
        </div>

        {blockers.length > 0 ? (
          <Alert className="border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning)]">
            <ShieldAlert />
            <AlertDescription className="flex flex-col gap-1 text-[var(--warning)]">
              {blockers.map((blocker) => <span key={blocker}>{blocker}</span>)}
            </AlertDescription>
          </Alert>
        ) : null}

        {items.length === 0 ? (
          <div className="rounded-xl border border-dashed p-5 text-sm leading-6 text-muted-foreground">
            Add syllabus, slide, assignment, or rubric metadata before final approval.
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border">
            {items.map((item) => (
              <SourceRow
                key={item.id}
                item={item}
                isSaving={updatingSourceId === item.id}
                onUpdate={(updates) => onUpdateSource(item.id, updates)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function SourceRow({
  item,
  isSaving,
  onUpdate,
}: {
  item: SourceInventoryItem
  isSaving: boolean
  onUpdate: (
    updates: Partial<
      Pick<
        SourceInventoryItem,
        | "permission_status"
        | "source_label"
        | "excluded"
        | "sensitive"
        | "notes"
      >
    >,
  ) => Promise<void>
}) {
  return (
    <article className="border-b p-4 last:border-b-0">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-medium">
            <FileText className="size-4 shrink-0 text-[var(--accent-strong)]" />
            <span className="truncate">{item.name}</span>
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>{item.mime_type}</span>
            <span>{formatBytes(item.size_bytes)}</span>
          </div>
        </div>
        <StatusBadge status={item.permission_status} />
      </div>

      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="grid gap-1 text-xs font-medium text-muted-foreground">
          Source label
          <select
            value={item.source_label}
            disabled={isSaving}
            onChange={(event) =>
              void onUpdate({ source_label: event.target.value as SourceLabel })
            }
            className="h-10 rounded-lg border bg-white px-3 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25"
          >
            {SOURCE_LABELS.map((label) => (
              <option key={label} value={label}>
                {label.replaceAll("-", " ")}
              </option>
            ))}
          </select>
        </label>

        <label className="flex min-h-10 items-center gap-2 text-xs text-muted-foreground sm:col-span-2">
          <Checkbox
            checked={item.sensitive}
            disabled={isSaving}
            onCheckedChange={(value) =>
              void onUpdate({ sensitive: Boolean(value) })
            }
            aria-label={`${item.name} sensitive flag`}
          />
          Sensitive or private material
        </label>

        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button
            type="button"
            size="sm"
            variant={item.permission_status === "approved" ? "default" : "outline"}
            disabled={isSaving}
            aria-pressed={item.permission_status === "approved"}
            onClick={() =>
              void onUpdate({
                permission_status: "approved",
                excluded: false,
              })
            }
          >
            {isSaving && item.permission_status !== "approved" ? (
              <Loader2 data-icon="inline-start" className="animate-spin" />
            ) : (
              <Check data-icon="inline-start" />
            )}
            Approve
          </Button>
          <Button
            type="button"
            size="sm"
            variant={item.excluded ? "default" : "outline"}
            disabled={isSaving}
            aria-pressed={item.excluded}
            onClick={() =>
              void onUpdate({
                permission_status: "excluded",
                excluded: true,
              })
            }
          >
            <Ban data-icon="inline-start" />
            Exclude
          </Button>
        </div>
      </div>

      {item.notes && (
        <p className="mt-3 rounded-lg bg-[var(--shell)] px-3 py-2 text-xs leading-5 text-muted-foreground">
          {item.notes}
        </p>
      )}
    </article>
  )
}

function StatusBadge({ status }: { status: SourcePermissionStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "status-badge",
        status === "approved" && "status-badge-success",
        status === "pending" && "status-badge-warning",
        status === "excluded" && "border-[var(--rule-strong)] text-muted-foreground",
      )}
    >
      {status}
    </Badge>
  )
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`
  }
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} KB`
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

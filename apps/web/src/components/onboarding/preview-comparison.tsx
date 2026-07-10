import { useState } from "react"
import {
  AlertTriangle,
  Check,
  ChevronDown,
  FileSearch,
  Loader2,
  MessageSquareText,
  Plus,
  X,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Textarea } from "@/components/ui/textarea"
import type {
  PreviewCase,
  PreviewDecisionValue,
  PromptTag,
  SourceLabel,
} from "@/lib/api"
import { cn } from "@/lib/utils"

type PreviewComparisonProps = {
  previewCases: PreviewCase[]
  updatingPreviewId: string | null
  isAddingCustomPreview: boolean
  onPreviewDecision: (
    previewCaseId: string,
    decision: PreviewDecisionValue,
    reason?: string,
  ) => Promise<void>
  onAddCustomPreview: (prompt: string, tag: PromptTag) => Promise<void>
}

const PROMPT_TAGS: Array<{ value: PromptTag; label: string }> = [
  { value: "source_grounding", label: "Source grounding" },
  { value: "academic_integrity", label: "Academic integrity" },
  { value: "misconception", label: "Misconception" },
  { value: "teaching_behavior", label: "Teaching behavior" },
  { value: "tone", label: "Tone" },
  { value: "other", label: "Other" },
]

export function PreviewComparison({
  previewCases,
  updatingPreviewId,
  isAddingCustomPreview,
  onPreviewDecision,
  onAddCustomPreview,
}: PreviewComparisonProps) {
  const [reasonByCase, setReasonByCase] = useState<Record<string, string>>({})
  const [customPrompt, setCustomPrompt] = useState("")
  const [customTag, setCustomTag] = useState<PromptTag>("teaching_behavior")

  const addCustom = async () => {
    const prompt = customPrompt.trim()
    if (!prompt || isAddingCustomPreview) {
      return
    }
    await onAddCustomPreview(prompt, customTag)
    setCustomPrompt("")
    setCustomTag("teaching_behavior")
  }

  return (
    <section className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Preview Evidence</h2>
          <p className="text-xs text-muted-foreground">
            Configured tutor responses, source audit, and professor decisions.
          </p>
        </div>
        <Badge variant="outline">{previewCases.length} cases</Badge>
      </div>

      {previewCases.length === 0 ? (
        <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
          Preview cases appear after draft policy generation.
        </div>
      ) : (
        <div className="space-y-3">
          {previewCases.map((preview) => (
            <PreviewCard
              key={preview.id}
              preview={preview}
              reason={reasonByCase[preview.id] ?? ""}
              isSaving={updatingPreviewId === preview.id}
              onReasonChange={(reason) =>
                setReasonByCase((current) => ({
                  ...current,
                  [preview.id]: reason,
                }))
              }
              onDecision={onPreviewDecision}
            />
          ))}
        </div>
      )}

      <div className="mt-4 rounded-lg border bg-background p-3">
        <div className="mb-2 text-sm font-medium">Professor custom prompt</div>
        <div className="grid gap-2">
          <Textarea
            value={customPrompt}
            onChange={(event) => setCustomPrompt(event.target.value)}
            className="min-h-20 text-sm"
            placeholder="Write a prompt to test before approval..."
            aria-label="Custom preview prompt"
          />
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={customTag}
              onChange={(event) => setCustomTag(event.target.value as PromptTag)}
              className="h-9 rounded-md border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Custom prompt tag"
            >
              {PROMPT_TAGS.map((tag) => (
                <option key={tag.value} value={tag.value}>
                  {tag.label}
                </option>
              ))}
            </select>
            <Button
              type="button"
              size="sm"
              onClick={() => void addCustom()}
              disabled={!customPrompt.trim() || isAddingCustomPreview}
            >
              {isAddingCustomPreview ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Plus data-icon="inline-start" />
              )}
              Add prompt
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

function PreviewCard({
  preview,
  reason,
  isSaving,
  onReasonChange,
  onDecision,
}: {
  preview: PreviewCase
  reason: string
  isSaving: boolean
  onReasonChange: (reason: string) => void
  onDecision: (
    previewCaseId: string,
    decision: PreviewDecisionValue,
    reason?: string,
  ) => Promise<void>
}) {
  return (
    <article className="rounded-lg border bg-background p-3">
      <div className="mb-3 flex gap-2 text-sm font-medium">
        <MessageSquareText className="mt-0.5 size-4 shrink-0 text-sky-700" />
        <span>{preview.prompt}</span>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{formatTag(preview.tag)}</Badge>
        <DecisionBadge decision={preview.decision} />
        <Badge variant="outline">policy v{preview.policy_version}</Badge>
        {preview.generated_at && (
          <span className="text-xs text-muted-foreground">
            {new Date(preview.generated_at).toLocaleString()}
          </span>
        )}
      </div>

      <ResponseBlock
        label="Configured response"
        body={preview.configured_response}
        tone="configured"
      />

      {preview.source_audit.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {preview.source_audit.map((source) => (
            <Badge
              key={`${preview.id}-${source.source_title}`}
              variant="outline"
              className={cn(labelTone(source.source_label))}
            >
              {source.source_label}
            </Badge>
          ))}
        </div>
      )}

      {preview.warnings.length > 0 && (
        <div className="mt-3 space-y-1 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          {preview.warnings.map((warning) => (
            <div key={warning} className="flex gap-2">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
              {warning}
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 grid gap-2">
        <Collapsible>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm font-medium">
            Generic comparison
            <ChevronDown className="size-4" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <ResponseBlock
              label="Generic response"
              body={preview.generic_response}
              tone="muted"
            />
          </CollapsibleContent>
        </Collapsible>

        <Collapsible>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm font-medium">
            Source audit
            <FileSearch className="size-4" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <div className="space-y-2">
              {preview.source_audit.map((source) => (
                <div
                  key={`${preview.id}-${source.url}`}
                  className="rounded-md border bg-muted/40 p-2 text-xs"
                >
                  <div className="font-medium">{source.source_title}</div>
                  <div className="mt-1 break-words text-muted-foreground">
                    {source.url}
                  </div>
                  <div className="mt-2 grid gap-1">
                    <span>Type: {source.source_type}</span>
                    <span>Label: {source.source_label}</span>
                    <span>Supports: {source.supports}</span>
                    <span>Conflict: {source.conflict_status}</span>
                    <span>Selected: {source.selection_reason}</span>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>

      <div className="mt-3 grid gap-2">
        <input
          value={reason}
          onChange={(event) => onReasonChange(event.target.value)}
          placeholder="Optional decision reason"
          className="h-9 rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={preview.decision === "accepted" ? "default" : "outline"}
            disabled={isSaving}
            onClick={() => void onDecision(preview.id, "accepted", reason)}
          >
            {isSaving ? (
              <Loader2 data-icon="inline-start" className="animate-spin" />
            ) : (
              <Check data-icon="inline-start" />
            )}
            Accept
          </Button>
          <Button
            type="button"
            size="sm"
            variant={preview.decision === "rejected" ? "default" : "outline"}
            disabled={isSaving}
            onClick={() => void onDecision(preview.id, "rejected", reason)}
          >
            <X data-icon="inline-start" />
            Reject
          </Button>
        </div>
      </div>
    </article>
  )
}

function ResponseBlock({
  label,
  body,
  tone,
}: {
  label: string
  body: string
  tone: "muted" | "configured"
}) {
  return (
    <div
      className={
        tone === "configured"
          ? "rounded-lg border border-emerald-200 bg-emerald-50 p-3"
          : "rounded-lg border bg-muted/50 p-3"
      }
    >
      <div className="mb-1 text-xs font-semibold uppercase tracking-normal text-muted-foreground">
        {label}
      </div>
      <p className="whitespace-pre-line text-sm leading-6">{body}</p>
    </div>
  )
}

function DecisionBadge({ decision }: { decision: PreviewDecisionValue }) {
  return (
    <Badge
      variant={decision === "accepted" ? "default" : "outline"}
      className={cn(decision === "rejected" && "border-red-200 text-red-700")}
    >
      {decision}
    </Badge>
  )
}

function formatTag(tag: PromptTag): string {
  return tag.replaceAll("_", " ")
}

function labelTone(label: SourceLabel): string {
  if (label === "course-approved") {
    return "border-emerald-200 text-emerald-700"
  }
  if (label === "system-suggested-trusted") {
    return "border-sky-200 text-sky-700"
  }
  if (label === "professor-approved-external") {
    return "border-violet-200 text-violet-700"
  }
  return "border-amber-200 text-amber-700"
}

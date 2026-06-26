import { MessageSquareText } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { PreviewCase } from "@/lib/api"

type PreviewComparisonProps = {
  previewCases: PreviewCase[]
}

export function PreviewComparison({ previewCases }: PreviewComparisonProps) {
  return (
    <section className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Preview Comparison</h2>
          <p className="text-xs text-muted-foreground">
            Generic behavior compared with configured tutor policy.
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
            <article key={preview.id} className="rounded-lg border bg-background p-3">
              <div className="mb-3 flex gap-2 text-sm font-medium">
                <MessageSquareText className="mt-0.5 size-4 shrink-0 text-sky-700" />
                {preview.prompt}
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <ResponseBlock
                  label="Generic"
                  body={preview.generic_response}
                  tone="muted"
                />
                <ResponseBlock
                  label="Configured"
                  body={preview.configured_response}
                  tone="configured"
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {preview.policy_signals.map((signal) => (
                  <Badge key={signal} variant="secondary">
                    {signal}
                  </Badge>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
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
      <p className="text-sm leading-6">{body}</p>
    </div>
  )
}

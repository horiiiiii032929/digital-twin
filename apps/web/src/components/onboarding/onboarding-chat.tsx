import { useMemo, useState } from "react"
import { Bot, Loader2, RotateCcw, SendHorizontal, UserRound } from "lucide-react"

import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container"
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input"
import { PromptSuggestion } from "@/components/ui/prompt-suggestion"
import { Button } from "@/components/ui/button"
import type { ChatMessage } from "@/lib/api/types"

type OnboardingChatProps = {
  messages: ChatMessage[]
  currentStep: string
  isLoading: boolean
  isSubmitting: boolean
  onSendMessage: (content: string) => Promise<void>
  onRestart: () => Promise<void>
}

const SUGGESTIONS_BY_STEP: Record<string, string[]> = {
  source_permissions: [
    "Use syllabus, public slides, and instructor-approved examples only.",
    "Exclude transcripts and any private student interactions for this sprint.",
  ],
  teaching_approach: [
    "Balance short explanations with guiding questions.",
    "Ask one diagnostic question before giving the full explanation.",
  ],
  academic_integrity: [
    "Refuse full graded-work answers, then offer hints or a similar example.",
    "Ask what the student tried first before giving conceptual help.",
  ],
  misconception_handling: [
    "Correct directly, then show a contrastive example.",
    "Ask the student to reconsider and point to the conflicting concept.",
  ],
  approval_criteria: [
    "Reject responses that use unapproved sources or solve graded work directly.",
    "Reject responses that mention private data or go beyond course policy.",
  ],
}

export function OnboardingChat({
  messages,
  currentStep,
  isLoading,
  isSubmitting,
  onSendMessage,
  onRestart,
}: OnboardingChatProps) {
  const [draft, setDraft] = useState("")
  const suggestions = useMemo(
    () => SUGGESTIONS_BY_STEP[currentStep] ?? [],
    [currentStep],
  )

  const submit = async () => {
    const content = draft.trim()

    if (!content || isSubmitting) {
      return
    }

    setDraft("")
    await onSendMessage(content)
  }

  const submitSuggestion = async (content: string) => {
    if (isSubmitting) {
      return
    }

    setDraft("")
    await onSendMessage(content)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col md:min-h-[620px]">
      <ChatContainerRoot className="min-h-0 flex-1 px-4 sm:min-h-[320px] sm:px-6 md:min-h-[420px]">
        <ChatContainerContent className="gap-0 py-5">
          {isLoading ? (
            <div className="flex items-center gap-2 border-y py-4 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Starting onboarding session
            </div>
          ) : (
            messages.map((message, index) => (
              <InterviewEntry
                key={`${message.role}-${index}`}
                message={message}
                index={index + 1}
              />
            ))
          )}
          <ChatContainerScrollAnchor />
        </ChatContainerContent>
      </ChatContainerRoot>

      <div className="border-t bg-[var(--workspace)] p-4 sm:px-6 sm:py-5">
        {suggestions.length > 0 && (
          <div className="mb-4">
            <div className="dossier-label mb-2">Suggested response patterns</div>
            <div className="grid gap-2 lg:grid-cols-2">
              {suggestions.map((suggestion) => (
                <PromptSuggestion
                  key={suggestion}
                  type="button"
                  size="sm"
                  className="h-auto max-w-full justify-start whitespace-normal rounded-md bg-white px-3 py-2.5 text-left leading-5"
                  disabled={isSubmitting || isLoading}
                  onClick={() => void submitSuggestion(suggestion)}
                >
                  {suggestion}
                </PromptSuggestion>
              ))}
            </div>
          </div>
        )}

        <label htmlFor="instructor-answer" className="dossier-label mb-2 block">
          Professor response
        </label>
        <PromptInput
          value={draft}
          onValueChange={setDraft}
          onSubmit={() => void submit()}
          disabled={isSubmitting || isLoading}
          isLoading={isSubmitting}
          className="rounded-md border-[var(--rule-strong)] bg-white"
        >
          <PromptInputTextarea
            id="instructor-answer"
            placeholder="Answer the current onboarding question..."
            aria-label="Onboarding answer"
          />
          <PromptInputActions className="justify-between">
            <PromptInputAction tooltip="Restart session">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Restart session"
                onClick={() => void onRestart()}
                disabled={isSubmitting || isLoading}
              >
                <RotateCcw data-icon="inline-start" />
              </Button>
            </PromptInputAction>
            <PromptInputAction tooltip="Send answer">
              <Button
                type="button"
                size="icon"
                aria-label="Send answer"
                onClick={() => void submit()}
                disabled={!draft.trim() || isSubmitting || isLoading}
              >
                {isSubmitting ? (
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                ) : (
                  <SendHorizontal data-icon="inline-start" />
                )}
              </Button>
            </PromptInputAction>
          </PromptInputActions>
        </PromptInput>
      </div>
    </div>
  )
}

function InterviewEntry({
  message,
  index,
}: {
  message: ChatMessage
  index: number
}) {
  const isInstructor = message.role === "instructor"
  const isSystem = message.role === "system"

  return (
    <article
      className={
        isInstructor
          ? "grid grid-cols-[40px_minmax(0,1fr)] gap-3 border-x border-t border-[#b9cdfb] bg-[var(--cobalt-soft)] px-4 py-4 last:border-b"
          : "grid grid-cols-[40px_minmax(0,1fr)] gap-3 border-t px-4 py-4 last:border-b"
      }
    >
      <div
        className={
          isInstructor
            ? "flex size-8 items-center justify-center border border-[#b9cdfb] bg-white text-[var(--cobalt)]"
            : "flex size-8 items-center justify-center bg-[var(--ink)] text-white"
        }
        aria-hidden="true"
      >
        {isInstructor ? (
          <UserRound className="size-4" />
        ) : (
          <Bot className="size-4" />
        )}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="dossier-label">
            {isInstructor ? "Professor decision" : isSystem ? "System record" : "Digital Twin prompt"}
          </span>
          <span className="text-[11px] font-medium tabular-nums text-muted-foreground">
            INT-{String(index).padStart(2, "0")}
          </span>
        </div>
        <p
          className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[var(--ink)]"
        aria-label={isInstructor ? "Instructor message" : "Assistant message"}
      >
        {message.content}
        </p>
      </div>
    </article>
  )
}

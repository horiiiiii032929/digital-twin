import { useState } from "react"
import { Loader2, RotateCcw, SendHorizontal, Sparkles, UserRound } from "lucide-react"

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
  onSendMessage: (content: string) => Promise<boolean>
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
  const suggestions = SUGGESTIONS_BY_STEP[currentStep] ?? []

  const submit = async () => {
    const content = draft.trim()

    if (!content || isSubmitting) {
      return
    }

    if (await onSendMessage(content)) {
      setDraft("")
    }
  }

  const submitSuggestion = async (content: string) => {
    if (isSubmitting) {
      return
    }

    await onSendMessage(content)
  }

  return (
    <div className="flex h-full min-h-[560px] flex-col">
      <ChatContainerRoot className="min-h-0 flex-1">
        <ChatContainerContent className="mx-auto w-full max-w-[760px] gap-7 px-5 py-7 sm:px-7 lg:py-8">
          {isLoading ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Starting setup session
            </div>
          ) : (
            messages.map((message, index) => (
              <InterviewEntry key={`${message.role}-${index}`} message={message} />
            ))
          )}
          <ChatContainerScrollAnchor />
        </ChatContainerContent>
      </ChatContainerRoot>

      <div className="border-t bg-white px-4 pb-5 pt-3 sm:px-6">
        <div className="mx-auto w-full max-w-[720px]">
          {suggestions.length > 0 ? (
            <div className="mb-3">
              <div className="mb-2 text-xs font-medium text-muted-foreground">Suggestions</div>
              <div className="grid gap-2 sm:grid-cols-2">
              {suggestions.map((suggestion) => (
                <PromptSuggestion
                  key={suggestion}
                  type="button"
                  size="sm"
                    className="h-auto min-w-0 justify-start whitespace-normal rounded-lg border-border bg-white px-3 py-2 text-left text-xs leading-5 hover:bg-[var(--subtle)]"
                  disabled={isSubmitting || isLoading}
                  onClick={() => void submitSuggestion(suggestion)}
                >
                  {suggestion}
                </PromptSuggestion>
              ))}
              </div>
            </div>
          ) : null}

          <label htmlFor="instructor-answer" className="sr-only">
            Reply to the setup assistant
          </label>
          <PromptInput
            value={draft}
            onValueChange={setDraft}
            onSubmit={() => void submit()}
            disabled={isSubmitting || isLoading}
            isLoading={isSubmitting}
            className="rounded-2xl border-border bg-white p-2 shadow-[var(--shadow-composer)] focus-within:border-[var(--accent-border)] focus-within:ring-2 focus-within:ring-[var(--accent-soft)]"
          >
            <PromptInputTextarea
              id="instructor-answer"
              placeholder="Reply to the setup assistant"
              aria-label="Setup assistant reply"
              className="min-h-12 px-2 py-2 text-sm"
            />
            <PromptInputActions className="justify-between px-0.5 pb-0.5">
              <PromptInputAction tooltip="Restart session">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
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
                  size="icon-lg"
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
    </div>
  )
}

function InterviewEntry({ message }: { message: ChatMessage }) {
  const isInstructor = message.role === "instructor"
  const isSystem = message.role === "system"

  return (
    <article className="grid grid-cols-[36px_minmax(0,1fr)] gap-3">
      <div
        className={isInstructor
          ? "flex size-8 items-center justify-center rounded-full bg-[var(--subtle)] text-muted-foreground"
          : "flex size-8 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent-strong)]"}
        aria-hidden="true"
      >
        {isInstructor ? (
          <UserRound className="size-4" />
        ) : (
          <Sparkles className="size-4" />
        )}
      </div>
      <div className="min-w-0">
        <div className="text-sm font-semibold">
          {isInstructor ? "Professor" : isSystem ? "System" : "Setup assistant"}
        </div>
        <p className="mt-1 max-w-[70ch] whitespace-pre-wrap text-sm leading-6 text-[var(--ink)]">
          {message.content}
        </p>
      </div>
    </article>
  )
}

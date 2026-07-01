import { useMemo, useState } from "react"
import { Bot, Loader2, RotateCcw, SendHorizontal, UserRound } from "lucide-react"

import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container"
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ui/message"
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input"
import { PromptSuggestion } from "@/components/ui/prompt-suggestion"
import { Button } from "@/components/ui/button"
import type { ChatMessage } from "@/lib/api"
import { cn } from "@/lib/utils"

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
    <div className="flex min-h-0 flex-1 flex-col">
      <ChatContainerRoot className="min-h-[260px] flex-1 px-4 sm:min-h-[420px]">
        <ChatContainerContent className="gap-4 py-4">
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Starting onboarding session
            </div>
          ) : (
            messages.map((message, index) => (
              <ChatBubble
                key={`${message.role}-${index}`}
                message={message}
              />
            ))
          )}
          <ChatContainerScrollAnchor />
        </ChatContainerContent>
      </ChatContainerRoot>

      <div className="border-t bg-background/80 p-3">
        {suggestions.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <PromptSuggestion
                key={suggestion}
                type="button"
                size="sm"
                className="h-auto max-w-full justify-start whitespace-normal rounded-lg text-left leading-5"
                disabled={isSubmitting || isLoading}
                onClick={() => void submitSuggestion(suggestion)}
              >
                {suggestion}
              </PromptSuggestion>
            ))}
          </div>
        )}

        <PromptInput
          value={draft}
          onValueChange={setDraft}
          onSubmit={() => void submit()}
          disabled={isSubmitting || isLoading}
          isLoading={isSubmitting}
          className="rounded-lg"
        >
          <PromptInputTextarea
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

function ChatBubble({ message }: { message: ChatMessage }) {
  const isInstructor = message.role === "instructor"

  return (
    <Message className={cn(isInstructor && "justify-end")}>
      {!isInstructor && (
        <MessageAvatar src="" alt="Assistant" fallback="DT" className="mt-1" />
      )}
      <MessageContent
        className={cn(
          "max-w-[82%] rounded-lg px-3 py-2 text-sm leading-6 shadow-none",
          isInstructor
            ? "bg-primary text-primary-foreground"
            : "border bg-card text-card-foreground",
        )}
        aria-label={isInstructor ? "Instructor message" : "Assistant message"}
      >
        {message.content}
      </MessageContent>
      {isInstructor && (
        <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
          <UserRound className="size-4" />
        </div>
      )}
      {message.role === "system" && <Bot className="size-4" />}
    </Message>
  )
}

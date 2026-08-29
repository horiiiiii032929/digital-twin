/**
 * THESIS: A student can ask one assigned course a question and inspect the exact
 * release-bound evidence; this refuses a generic multi-tool chatbot.
 * OWN-WORLD: A 216px cool-neutral rail, true-white conversation canvas,
 * near-black actions, restrained iris selection, compact open rows, and one
 * elevated composer from the shared grounded workspace.
 * STORY: Select the available course, start or restore its current conversation,
 * ask a question, and open validated citation lineage beside the answer.
 * FIRST VIEWPORT: Course rail, wide centered transcript, minimal course/release
 * header, and a citation inspector only after selection; mobile uses sheets.
 * FORM: User-delegated familiar-LLM canon, accepted product-wide composition C.
 */

import { useEffect, useRef, useState, type RefObject } from "react"
import {
  AlertCircle,
  Bell,
  BellOff,
  BookOpen,
  FileText,
  Menu,
  MessageCircle,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
  UserRound,
  X,
} from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import type { StudentWorkspaceController } from "@/hooks/use-student-workspace"
import type {
  StudentChatMessage,
  StudentCitation,
  StudentCourse,
  StudentProactiveMessageView,
} from "@/lib/api"
import { loadStudentCitationCrop } from "@/lib/api"
import { cn } from "@/lib/utils"
import { WorkspaceBrand } from "@/components/workspace/workspace-brand"

const SESSION_AUTH_ENABLED = import.meta.env.VITE_AUTH_MODE === "session"

export function StudentWorkspace({
  controller,
}: {
  controller: StudentWorkspaceController
}) {
  const [citationSheetOpen, setCitationSheetOpen] = useState(false)
  const [citationPanelOpen, setCitationPanelOpen] = useState(false)
  const [courseMenuOpen, setCourseMenuOpen] = useState(false)
  const [outreachOpen, setOutreachOpen] = useState(false)
  const citationTriggerRef = useRef<HTMLButtonElement | null>(null)
  const courseMenuTriggerRef = useRef<HTMLButtonElement | null>(null)
  const outreachTriggerRef = useRef<HTMLButtonElement | null>(null)
  const {
    courses,
    activeCourse,
    conversation,
    messages,
    citationsByMessage,
    selectedCitation,
    draft,
    error,
    isLoadingCourses,
    isLoadingConversation,
    isSubmitting,
    outreachMessages,
    inAppOutreachEnabled,
    isLoadingOutreach,
    isUpdatingOutreach,
    outreachError,
    requiresNewConversation,
    setDraft,
    reload,
    selectCourse,
    startNewConversation,
    startCurrentRelease,
    sendMessage,
    refreshOutreach,
    setInAppOutreachEnabled,
    markOutreachRead,
    dismissOutreach,
    selectCitation,
  } = controller

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 1024px)")
    const closeMobileSurfacesOnDesktop = (event: MediaQueryListEvent) => {
      if (!event.matches) return
      setCourseMenuOpen(false)
      setCitationSheetOpen(false)
    }
    desktop.addEventListener("change", closeMobileSurfacesOnDesktop)
    return () => desktop.removeEventListener("change", closeMobileSurfacesOnDesktop)
  }, [])

  useEffect(() => {
    if (!selectedCitation) {
      setCitationPanelOpen(false)
      setCitationSheetOpen(false)
    }
  }, [selectedCitation])

  const openCitation = (
    messageId: string,
    citationId: string,
    trigger: HTMLButtonElement,
  ) => {
    citationTriggerRef.current = trigger
    selectCitation(messageId, citationId)
    if (window.matchMedia("(max-width: 1023px)").matches) {
      setCitationSheetOpen(true)
    } else {
      setCitationPanelOpen(true)
    }
  }

  return (
    <main className="h-dvh min-w-0 overflow-hidden bg-white text-foreground">
      <div
        className={cn(
          "grid h-full min-h-0 min-w-0 lg:overflow-hidden",
          citationPanelOpen
            ? "lg:grid-cols-[216px_minmax(0,1fr)_400px]"
            : "lg:grid-cols-[216px_minmax(0,1fr)]",
        )}
      >
        <CourseRail
          className="hidden lg:flex"
          courses={courses}
          activeCourse={activeCourse}
          messages={messages}
          isLoading={isLoadingCourses}
          isStartingConversation={isLoadingConversation}
          isSubmitting={isSubmitting}
          onSelectCourse={selectCourse}
          onNewConversation={startNewConversation}
        />

        <section className="flex min-h-0 min-w-0 flex-col bg-white">
          <StudentHeader
            activeCourse={activeCourse}
            citationAvailable={Boolean(selectedCitation)}
            citationPanelOpen={citationPanelOpen}
            unreadOutreachCount={
              outreachMessages.filter(
                (item) => item.message.status === "delivered",
              ).length
            }
            menuTriggerRef={courseMenuTriggerRef}
            onOpenMenu={() => setCourseMenuOpen(true)}
            onOpenMobileCitation={() => setCitationSheetOpen(true)}
            onToggleCitation={() => setCitationPanelOpen((open) => !open)}
            outreachTriggerRef={outreachTriggerRef}
            onOpenOutreach={() => setOutreachOpen(true)}
          />

          {isLoadingCourses ? (
            <WorkspaceLoading />
          ) : error && courses.length === 0 ? (
            <WorkspaceUnavailable error={error.message} onRetry={reload} />
          ) : courses.length === 0 ? (
            <NoCourses onRetry={reload} />
          ) : (
            <>
              <Conversation
                course={activeCourse}
                messages={messages}
                citationsByMessage={citationsByMessage}
                selectedCitation={selectedCitation}
                isLoading={isLoadingConversation}
                onOpenCitation={openCitation}
              />
              <Composer
                course={activeCourse}
                conversationAvailable={Boolean(conversation)}
                value={draft}
                error={error?.message ?? null}
                errorScope={error?.scope ?? null}
                requiresNewConversation={requiresNewConversation}
                isLoading={isLoadingConversation}
                isSubmitting={isSubmitting}
                onValueChange={setDraft}
                onSubmit={sendMessage}
                onRecover={
                  requiresNewConversation
                    ? startCurrentRelease
                    : error?.scope === "message"
                      ? sendMessage
                      : reload
                }
              />
            </>
          )}
        </section>

        {citationPanelOpen ? (
          <CitationPanel
            citation={selectedCitation}
            course={activeCourse}
            className="hidden min-h-0 border-l lg:flex"
            onClose={() => setCitationPanelOpen(false)}
          />
        ) : null}
      </div>

      <DialogPrimitive.Root open={courseMenuOpen} onOpenChange={setCourseMenuOpen}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-20 bg-black/15 lg:hidden" />
          <DialogPrimitive.Content
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              courseMenuTriggerRef.current?.focus()
            }}
            className="fixed inset-y-0 left-0 z-30 w-[min(88vw,320px)] overflow-hidden border-r bg-[var(--shell)] shadow-[12px_0_40px_rgba(32,33,35,0.12)] outline-none lg:hidden"
          >
            <DialogPrimitive.Title className="sr-only">
              Student course navigation
            </DialogPrimitive.Title>
            <CourseRail
              className="flex h-full"
              courses={courses}
              activeCourse={activeCourse}
              messages={messages}
              isLoading={isLoadingCourses}
              isStartingConversation={isLoadingConversation}
              isSubmitting={isSubmitting}
              onSelectCourse={async (courseId) => {
                await selectCourse(courseId)
                setCourseMenuOpen(false)
              }}
              onNewConversation={async () => {
                await startNewConversation()
                setCourseMenuOpen(false)
              }}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute top-2.5 right-2.5"
              aria-label="Close course navigation"
              onClick={() => setCourseMenuOpen(false)}
            >
              <X aria-hidden="true" />
            </Button>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      <DialogPrimitive.Root
        open={citationSheetOpen}
        onOpenChange={setCitationSheetOpen}
      >
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-20 bg-black/15 lg:hidden" />
          <DialogPrimitive.Content
            aria-describedby={undefined}
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              citationTriggerRef.current?.focus()
            }}
            className="fixed inset-x-0 bottom-0 z-30 max-h-[78dvh] overflow-hidden rounded-t-2xl border-t bg-white shadow-[0_-12px_40px_rgba(32,33,35,0.14)] outline-none lg:hidden"
          >
            <div
              aria-hidden="true"
              className="absolute top-2 left-1/2 z-10 h-1 w-9 -translate-x-1/2 rounded-full bg-[var(--rule-strong)]"
            />
            <CitationPanel
              citation={selectedCitation}
              course={activeCourse}
              className="flex max-h-[78dvh]"
              dialogTitle
              onClose={() => setCitationSheetOpen(false)}
            />
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      <DialogPrimitive.Root open={outreachOpen} onOpenChange={setOutreachOpen}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-20 bg-black/15" />
          <DialogPrimitive.Content
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              outreachTriggerRef.current?.focus()
            }}
            className="fixed inset-y-0 right-0 z-30 flex w-[min(94vw,420px)] flex-col border-l bg-white shadow-[-12px_0_40px_rgba(32,33,35,0.14)] outline-none"
          >
            <OutreachPanel
              messages={outreachMessages}
              enabled={inAppOutreachEnabled}
              isLoading={isLoadingOutreach}
              isUpdating={isUpdatingOutreach}
              error={outreachError}
              onClose={() => setOutreachOpen(false)}
              onRefresh={refreshOutreach}
              onEnabledChange={setInAppOutreachEnabled}
              onMarkRead={markOutreachRead}
              onDismiss={dismissOutreach}
            />
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </main>
  )
}

function StudentHeader({
  activeCourse,
  citationAvailable,
  citationPanelOpen,
  unreadOutreachCount,
  menuTriggerRef,
  onOpenMenu,
  onOpenMobileCitation,
  onToggleCitation,
  outreachTriggerRef,
  onOpenOutreach,
}: {
  activeCourse: StudentCourse | null
  citationAvailable: boolean
  citationPanelOpen: boolean
  unreadOutreachCount: number
  menuTriggerRef: RefObject<HTMLButtonElement | null>
  onOpenMenu: () => void
  onOpenMobileCitation: () => void
  onToggleCitation: () => void
  outreachTriggerRef: RefObject<HTMLButtonElement | null>
  onOpenOutreach: () => void
}) {
  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b bg-white pl-3 pr-14 sm:pl-5 xl:pr-56">
      <div className="flex min-w-0 items-center gap-2.5">
        <Button
          ref={menuTriggerRef}
          type="button"
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open course navigation"
          onClick={onOpenMenu}
        >
          <Menu aria-hidden="true" />
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold tracking-[-0.015em] sm:text-base">
            {activeCourse?.title ?? "Student tutor"}
          </h1>
          {activeCourse ? (
            <span className="block text-xs font-medium text-[var(--success)] sm:hidden">
              Current release
            </span>
          ) : null}
        </div>
        {activeCourse ? (
          <span className="hidden items-center gap-1.5 text-xs font-medium text-[var(--success)] sm:inline-flex">
            <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
            Current release
          </span>
        ) : null}
      </div>
      <div className="flex items-center gap-1.5">
        {!SESSION_AUTH_ENABLED ? (
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <a href="/" aria-label="Open tutor setup">
              Tutor setup
            </a>
          </Button>
        ) : null}
        <Button
          ref={outreachTriggerRef}
          type="button"
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={
            unreadOutreachCount > 0
              ? `Open tutor check-ins, ${unreadOutreachCount} unread`
              : "Open tutor check-ins"
          }
          onClick={onOpenOutreach}
        >
          <Bell aria-hidden="true" />
          {unreadOutreachCount > 0 ? (
            <span className="absolute top-1 right-1 flex min-w-4 items-center justify-center rounded-full bg-[var(--accent-strong)] px-1 text-[10px] leading-4 font-bold text-white">
              {Math.min(unreadOutreachCount, 9)}
            </span>
          ) : null}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="lg:hidden"
          disabled={!citationAvailable}
          aria-label="Open citation details"
          onClick={onOpenMobileCitation}
        >
          <PanelRightOpen data-icon="inline-start" />
          Sources
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="hidden lg:inline-flex"
          disabled={!citationAvailable}
          aria-label={citationPanelOpen ? "Close citation details" : "Open citation details"}
          aria-pressed={citationPanelOpen}
          onClick={onToggleCitation}
        >
          {citationPanelOpen ? (
            <PanelRightClose data-icon="inline-start" />
          ) : (
            <PanelRightOpen data-icon="inline-start" />
          )}
          Sources
        </Button>
      </div>
    </header>
  )
}

function OutreachPanel({
  messages,
  enabled,
  isLoading,
  isUpdating,
  error,
  onClose,
  onRefresh,
  onEnabledChange,
  onMarkRead,
  onDismiss,
}: {
  messages: StudentProactiveMessageView[]
  enabled: boolean
  isLoading: boolean
  isUpdating: boolean
  error: string | null
  onClose: () => void
  onRefresh: () => Promise<void>
  onEnabledChange: (enabled: boolean) => Promise<void>
  onMarkRead: (messageId: string) => Promise<void>
  onDismiss: (messageId: string) => Promise<void>
}) {
  return (
    <>
      <div className="flex min-h-14 items-center justify-between gap-3 border-b pl-5 pr-14">
        <div className="min-w-0">
          <DialogPrimitive.Title className="text-sm font-semibold">
            Tutor check-ins
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-0.5 text-xs text-muted-foreground">
            Private messages initiated by your course Digital Twin
          </DialogPrimitive.Description>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Close tutor check-ins"
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </div>

      <div className="border-b bg-[var(--shell)] p-4">
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border bg-white p-3.5">
          <Checkbox
            checked={enabled}
            disabled={isUpdating}
            aria-label="Allow private tutor check-ins"
            onCheckedChange={(checked) =>
              void onEnabledChange(checked === true)
            }
          />
          <span className="min-w-0">
            <span className="block text-sm font-semibold">
              Allow private in-app check-ins
            </span>
            <span className="mt-1 block text-xs leading-5 text-muted-foreground">
              At most three per week, with quiet hours from 10 PM to 8 AM. You
              can turn this off at any time.
            </span>
          </span>
        </label>
        <p className="mt-2.5 px-1 text-xs leading-5 text-muted-foreground">
          Discord delivery is not connected yet. Individual learning details
          will never be posted to a shared channel.
        </p>
      </div>

      <div className="flex items-center justify-between gap-3 px-5 py-3">
        <h2 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          Inbox
        </h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={isLoading}
          onClick={() => void onRefresh()}
        >
          <RefreshCcw data-icon="inline-start" />
          Refresh
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-5">
        {error ? (
          <Alert variant="destructive" className="mb-3">
            <AlertCircle aria-hidden="true" />
            <AlertTitle>Check-ins unavailable</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {isLoading && messages.length === 0 ? (
          <div className="space-y-3" aria-label="Loading tutor check-ins">
            <div className="h-32 animate-pulse rounded-xl bg-[var(--subtle)]" />
            <div className="h-32 animate-pulse rounded-xl bg-[var(--subtle)]" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center px-8 text-center">
            <span className="flex size-11 items-center justify-center rounded-full bg-[var(--subtle)] text-muted-foreground">
              {enabled ? (
                <Bell className="size-5" aria-hidden="true" />
              ) : (
                <BellOff className="size-5" aria-hidden="true" />
              )}
            </span>
            <h3 className="mt-3 text-sm font-semibold">
              {enabled ? "No check-ins yet" : "Check-ins are off"}
            </h3>
            <p className="mt-1.5 max-w-64 text-xs leading-5 text-muted-foreground">
              {enabled
                ? "When your professor-approved tutor schedules a useful review, it will appear here."
                : "Turn them on above if you want the tutor to initiate occasional study follow-ups."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map(({ message, citations }) => (
              <article
                key={message.id}
                className={cn(
                  "rounded-xl border p-4",
                  message.status === "delivered"
                    ? "border-[var(--accent-strong)]/25 bg-[var(--accent-soft)]/40"
                    : "bg-white",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Sparkles className="size-3.5" aria-hidden="true" />
                    Professor Digital Twin
                  </span>
                  <time
                    dateTime={message.created_at}
                    className="shrink-0 text-[11px] text-muted-foreground"
                  >
                    {formatOutreachTime(message.created_at)}
                  </time>
                </div>
                <p className="mt-3 whitespace-pre-line text-sm leading-6">
                  {message.content}
                </p>
                {citations[0] ? (
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    Source: {citations[0].title} · {citations[0].locator}
                  </p>
                ) : null}
                <div className="mt-3 flex items-center justify-end gap-2">
                  {message.status === "delivered" ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void onMarkRead(message.id)}
                    >
                      Mark read
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => void onDismiss(message.id)}
                  >
                    Dismiss
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function formatOutreachTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Recently"
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date)
}

function CourseRail({
  courses,
  activeCourse,
  messages,
  isLoading,
  isStartingConversation,
  isSubmitting,
  onSelectCourse,
  onNewConversation,
  className,
}: {
  courses: StudentCourse[]
  activeCourse: StudentCourse | null
  messages: StudentChatMessage[]
  isLoading: boolean
  isStartingConversation: boolean
  isSubmitting: boolean
  onSelectCourse: (courseId: string) => Promise<void>
  onNewConversation: () => Promise<void>
  className?: string
}) {
  const conversationTitle =
    messages.find((message) => message.role === "student")?.content ??
    "Current conversation"

  return (
    <aside className={cn("min-h-0 flex-col border-r bg-[var(--shell)]", className)}>
      <WorkspaceBrand className="pr-14 lg:pr-4" />
      <div className="p-3">
        <h2 className="px-2 pb-2 text-xs font-semibold text-muted-foreground">
          Current course
        </h2>
        <div className="space-y-1">
          {isLoading ? (
            <div className="h-16 animate-pulse rounded-xl bg-[var(--subtle)]" />
          ) : (
            courses.map((course) => (
              <button
                key={course.course_id}
                type="button"
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-2.5 py-2.5 text-left outline-none transition-colors hover:bg-[var(--subtle)] focus-visible:ring-2 focus-visible:ring-ring/30",
                  activeCourse?.course_id === course.course_id &&
                    "bg-[var(--accent-soft)]",
                )}
                aria-pressed={activeCourse?.course_id === course.course_id}
                disabled={isStartingConversation || isSubmitting}
                onClick={() => void onSelectCourse(course.course_id)}
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
                  <BookOpen className="size-4.5" aria-hidden="true" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm leading-5 font-semibold">
                    {course.title}
                  </span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-xs text-[var(--success)]">
                    <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
                    Available
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="px-3">
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={!activeCourse || isStartingConversation || isSubmitting}
          onClick={() => void onNewConversation()}
        >
          <Plus data-icon="inline-start" />
          New chat
        </Button>
      </div>

      {activeCourse ? (
        <div className="mt-5 min-h-0 px-3">
          <h2 className="px-2 pb-2 text-xs font-semibold text-muted-foreground">
            Current chat
          </h2>
          <div className="flex items-center gap-2 rounded-lg bg-[var(--subtle)] px-2.5 py-2 text-sm text-foreground">
            <MessageCircle className="size-4 shrink-0 text-[var(--accent-strong)]" aria-hidden="true" />
            <span className="truncate">{conversationTitle}</span>
          </div>
        </div>
      ) : null}

      <p className="mt-auto border-t px-4 py-3 text-xs leading-5 text-muted-foreground">
        {SESSION_AUTH_ENABLED
          ? "Course access follows your signed-in account."
          : "Synthetic local account · Chat ID stays in this browser."}
      </p>
    </aside>
  )
}

function Conversation({
  course,
  messages,
  citationsByMessage,
  selectedCitation,
  isLoading,
  onOpenCitation,
}: {
  course: StudentCourse | null
  messages: StudentChatMessage[]
  citationsByMessage: Record<string, StudentCitation[]>
  selectedCitation: StudentCitation | null
  isLoading: boolean
  onOpenCitation: (
    messageId: string,
    citationId: string,
    trigger: HTMLButtonElement,
  ) => void
}) {
  return (
    <ChatContainerRoot
      aria-label="Student tutoring conversation"
      className="min-h-0 flex-1 bg-white"
    >
      <ChatContainerContent className="mx-auto w-full max-w-[800px] gap-7 px-4 py-7 sm:px-8 sm:py-9">
        {course ? <TutorWelcome course={course} /> : null}
        {isLoading ? <ConversationLoading /> : null}
        {messages.map((message) => (
          <ConversationMessage
            key={message.id}
            message={message}
            citations={citationsByMessage[message.id] ?? []}
            selectedCitationId={selectedCitation?.id ?? null}
            onOpenCitation={onOpenCitation}
          />
        ))}
        <ChatContainerScrollAnchor />
      </ChatContainerContent>
    </ChatContainerRoot>
  )
}

function TutorWelcome({ course }: { course: StudentCourse }) {
  return (
    <article className="flex gap-3.5">
      <TutorAvatar />
      <div className="min-w-0 max-w-[70ch] pt-0.5">
        <h2 className="text-sm font-semibold">Tutor</h2>
        <p className="mt-1 text-sm leading-6 text-foreground">
          Hi. I&apos;m your course tutor for {course.title}. I answer only from
          approved course material.
        </p>
      </div>
    </article>
  )
}

function ConversationMessage({
  message,
  citations,
  selectedCitationId,
  onOpenCitation,
}: {
  message: StudentChatMessage
  citations: StudentCitation[]
  selectedCitationId: string | null
  onOpenCitation: (
    messageId: string,
    citationId: string,
    trigger: HTMLButtonElement,
  ) => void
}) {
  const isTutor = message.role === "tutor"
  const isSafeAction = isTutor && message.action !== "answer"

  return (
    <article className="flex gap-3.5">
      {isTutor ? (
        <TutorAvatar />
      ) : (
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--subtle)] text-muted-foreground">
          <UserRound className="size-4.5" aria-hidden="true" />
        </span>
      )}
      <div className="min-w-0 max-w-[70ch] pt-0.5">
        <h2 className="text-sm font-semibold">{isTutor ? "Tutor" : "You"}</h2>
        <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-foreground">
          {message.content}
        </p>
        {isSafeAction ? (
          <span className="mt-2 inline-flex rounded-md bg-[var(--warning-soft)] px-2 py-1 text-xs font-medium text-[var(--warning)]">
            Safe action · {formatAction(message.action)}
          </span>
        ) : null}
        {citations.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Answer citations">
            {citations.map((citation, index) => (
              <button
                key={citation.id}
                type="button"
                className={cn(
                  "flex min-h-11 min-w-11 items-center justify-center rounded-md px-1.5 py-0.5 text-xs font-semibold text-[var(--accent-strong)] outline-none hover:bg-[var(--accent-soft)] focus-visible:ring-2 focus-visible:ring-ring/30 lg:min-h-7 lg:min-w-7",
                  citation.id === selectedCitationId && "bg-[var(--accent-soft)]",
                )}
                aria-label={`Open citation ${index + 1}: ${citation.title}, ${citation.locator}`}
                onClick={(event) =>
                  onOpenCitation(message.id, citation.id, event.currentTarget)
                }
              >
                [{index + 1}]
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  )
}

function TutorAvatar() {
  return (
    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent-strong)]">
      <Sparkles className="size-4.5" aria-hidden="true" />
    </span>
  )
}

function Composer({
  course,
  conversationAvailable,
  value,
  error,
  errorScope,
  requiresNewConversation,
  isLoading,
  isSubmitting,
  onValueChange,
  onSubmit,
  onRecover,
}: {
  course: StudentCourse | null
  conversationAvailable: boolean
  value: string
  error: string | null
  errorScope: "workspace" | "message" | null
  requiresNewConversation: boolean
  isLoading: boolean
  isSubmitting: boolean
  onValueChange: (value: string) => void
  onSubmit: () => Promise<void>
  onRecover: () => Promise<void>
}) {
  const disabled =
    !course || !conversationAvailable || isLoading || requiresNewConversation

  return (
    <div className="border-t bg-white px-3 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 sm:px-6">
      <div className="mx-auto w-full max-w-[800px]">
        {error ? (
          <Alert variant="destructive" className="mb-3">
            <AlertCircle />
            <AlertTitle>
              {requiresNewConversation
                ? "This course release changed"
                : errorScope === "workspace"
                  ? "Course conversation unavailable"
                  : "The question was not sent"}
            </AlertTitle>
            <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
              <span>
                {error}
                {value.trim() ? " Your text is still here." : ""}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-11 sm:min-h-8"
                onClick={() => void onRecover()}
              >
                <RefreshCcw data-icon="inline-start" />
                {requiresNewConversation
                  ? "Start current release"
                  : errorScope === "workspace"
                    ? "Retry course"
                  : "Try again"}
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}
        <PromptInput
          value={value}
          onValueChange={onValueChange}
          onSubmit={() => void onSubmit()}
          isLoading={isSubmitting}
          disabled={disabled || isSubmitting}
          className="rounded-2xl border bg-white p-2 shadow-[var(--shadow-composer)] focus-within:border-[var(--accent-border)] focus-within:ring-2 focus-within:ring-ring/20"
        >
          <PromptInputTextarea
            placeholder={isLoading ? "Opening the course conversation…" : "Ask about this course"}
            aria-label="Ask about this course"
            maxLength={8000}
            className="min-h-12 px-2 py-2.5 text-sm"
          />
          <PromptInputActions className="justify-end px-1 pb-1">
            <PromptInputAction tooltip="Send question">
              <Button
                type="button"
                size="icon-lg"
                className="size-11 sm:size-9"
                aria-label="Send question"
                disabled={disabled || isSubmitting || !value.trim()}
                onClick={() => void onSubmit()}
              >
                <Send className="size-4" aria-hidden="true" />
              </Button>
            </PromptInputAction>
          </PromptInputActions>
        </PromptInput>
        <p className="px-2 pt-2 text-xs leading-5 text-muted-foreground">
          Answers use the current published course release.
        </p>
      </div>
    </div>
  )
}

function CitationPanel({
  citation,
  course,
  className,
  dialogTitle = false,
  onClose,
}: {
  citation: StudentCitation | null
  course: StudentCourse | null
  className?: string
  dialogTitle?: boolean
  onClose?: () => void
}) {
  const [cropUrl, setCropUrl] = useState<string | null>(null)
  const [cropError, setCropError] = useState<string | null>(null)

  useEffect(() => {
    setCropUrl(null)
    setCropError(null)
    if (!citation?.crop_ref) return

    let active = true
    let objectUrl: string | null = null
    void loadStudentCitationCrop(citation.message_id, citation.id)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setCropUrl(objectUrl)
      })
      .catch((error: unknown) => {
        if (active) {
          setCropError(
            error instanceof Error ? error.message : "Source region unavailable.",
          )
        }
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [citation?.crop_ref, citation?.id, citation?.message_id])

  const title = (
    <h2 className="text-sm font-semibold">Sources for this answer</h2>
  )

  return (
    <aside
      aria-label="Sources for this answer"
      className={cn("min-w-0 flex-col overflow-y-auto bg-white", className)}
    >
      <div className="flex min-h-14 items-center justify-between gap-3 border-b px-5">
        {dialogTitle ? (
          <DialogPrimitive.Title asChild>{title}</DialogPrimitive.Title>
        ) : (
          title
        )}
        {onClose ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-11"
            aria-label="Close sources"
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </Button>
        ) : null}
      </div>

      <div className="p-4 sm:p-5">
        {citation ? (
          <div className="rounded-xl border border-[var(--accent-border)] p-4">
            <div className="flex items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                <FileText className="size-4.5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold">{citation.title}</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {citation.locator}
                </p>
              </div>
            </div>
            {citation.crop_ref ? (
              <div className="mt-4 overflow-hidden rounded-lg border bg-[var(--shell)]">
                {cropUrl ? (
                  <a
                    href={cropUrl}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Open original source region for ${citation.title}`}
                  >
                    <img
                      src={cropUrl}
                      alt={`Original source region from ${citation.locator}`}
                      className="max-h-72 w-full object-contain"
                    />
                  </a>
                ) : cropError ? (
                  <p className="px-3 py-4 text-sm text-muted-foreground">
                    {cropError}
                  </p>
                ) : (
                  <p className="px-3 py-4 text-sm text-muted-foreground">
                    Loading original source region…
                  </p>
                )}
              </div>
            ) : null}
            <dl className="mt-5 grid gap-3 border-t pt-4 text-sm">
              {citation.page ? (
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">
                    Page and region
                  </dt>
                  <dd className="mt-0.5">
                    Page {citation.page}
                    {citation.region_kind
                      ? ` · ${citation.region_kind.replaceAll("-", " ")}`
                      : ""}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt className="text-xs font-medium text-muted-foreground">
                  Source version
                </dt>
                <dd className="mt-0.5">{citation.source_version}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted-foreground">
                  Release lineage
                </dt>
                <dd className="mt-0.5">
                  {citation.release_id === course?.release_id
                    ? "Current course release"
                    : "Conversation release"}
                </dd>
              </div>
            </dl>
          </div>
        ) : (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-xl bg-[var(--shell)] px-6 text-center">
            <span className="flex size-11 items-center justify-center rounded-full bg-white text-muted-foreground">
              <FileText className="size-5" aria-hidden="true" />
            </span>
            <h3 className="mt-4 text-sm font-semibold">No citation selected</h3>
            <p className="mt-1 max-w-[30ch] text-sm leading-6 text-muted-foreground">
              Citations appear after a grounded answer. Select a citation marker
              to inspect its source and release lineage.
            </p>
          </div>
        )}
      </div>
    </aside>
  )
}

function WorkspaceLoading() {
  return (
    <div className="mx-auto flex w-full max-w-[800px] flex-1 flex-col gap-6 px-5 py-8 sm:px-8">
      <div className="h-20 animate-pulse rounded-xl bg-[var(--shell)]" />
      <div className="h-16 animate-pulse rounded-xl bg-[var(--shell)]" />
      <div className="h-20 animate-pulse rounded-xl bg-[var(--shell)]" />
    </div>
  )
}

function ConversationLoading() {
  return (
    <div className="flex gap-3.5" aria-label="Loading conversation">
      <span className="size-9 shrink-0 animate-pulse rounded-full bg-[var(--subtle)]" />
      <div className="w-full max-w-md space-y-2 pt-1">
        <div className="h-3 w-20 animate-pulse rounded bg-[var(--subtle)]" />
        <div className="h-3 w-full animate-pulse rounded bg-[var(--subtle)]" />
        <div className="h-3 w-3/4 animate-pulse rounded bg-[var(--subtle)]" />
      </div>
    </div>
  )
}

function WorkspaceUnavailable({
  error,
  onRetry,
}: {
  error: string
  onRetry: () => Promise<void>
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-5">
      <Alert variant="destructive" className="max-w-lg">
        <AlertCircle />
        <AlertTitle>Student workspace unavailable</AlertTitle>
        <AlertDescription>
          <p>{error}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => void onRetry()}
          >
            <RefreshCcw data-icon="inline-start" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  )
}

function NoCourses({ onRetry }: { onRetry: () => Promise<void> }) {
  return (
    <div className="flex flex-1 items-center justify-center p-5 text-center">
      <div className="max-w-md">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-[var(--shell)] text-muted-foreground">
          <BookOpen className="size-5" aria-hidden="true" />
        </span>
        <h2 className="mt-4 text-base font-semibold">No published course available</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          This synthetic student is not assigned to a course with a current
          published Digital Twin release.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => void onRetry()}
        >
          <RefreshCcw data-icon="inline-start" />
          Check again
        </Button>
      </div>
    </div>
  )
}

function formatAction(action: string): string {
  return action.replaceAll("_", " ").replaceAll("-", " ")
}

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
  ArrowUpRight,
  Bell,
  BellOff,
  BookOpen,
  Clock3,
  FileCheck2,
  FileText,
  Menu,
  MessageCircle,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
  Target,
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
  AutonomousGoalV1,
  ClarificationRequestV1,
  StudentChatMessage,
  StudentCitation,
  StudentCourse,
  StudentProactiveMessageView,
  StudentLearnerEvidence,
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
  const composerRef = useRef<HTMLDivElement | null>(null)
  const focusReplyRef = useRef(false)
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
    outreachReply,
    autonomousGoals,
    learnerEvidence,
    evidenceStatus,
    citationsStatus,
    retryEvidence,
    retryCitations,
    pendingClarification,
    inAppOutreachEnabled,
    outreachSnoozedUntil,
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
    chooseClarification,
    refreshOutreach,
    setInAppOutreachEnabled,
    snoozeOutreach,
    markOutreachRead,
    dismissOutreach,
    replyToOutreach,
    cancelOutreachReply,
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
    <main className="h-dvh min-w-0 overflow-hidden bg-[var(--shell)] text-foreground">
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

        <section className="workspace-canvas flex min-h-0 min-w-0 flex-col">
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

          {controller.conversationHistory.length > 1 ? (
            <label className="flex min-w-0 items-center gap-3 border-b px-4 py-2 text-sm sm:px-6">
              <span className="shrink-0 text-muted-foreground">Saved chats</span>
              <select
                aria-label="Resume a saved chat in this course version"
                className="min-w-0 flex-1 rounded-md border bg-background px-2 py-1.5 focus-visible:outline-2 focus-visible:outline-ring"
                value={conversation?.id ?? ""}
                disabled={isLoadingConversation || isSubmitting}
                onChange={(event) => void controller.selectConversation(event.target.value)}
              >
                {!conversation ? <option value="">Loading conversation…</option> : null}
                {controller.conversationHistory.map((item) => (
                  <option key={item.id} value={item.id}>
                    Started {new Date(item.created_at).toLocaleString("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {isLoadingCourses ? (
            <WorkspaceLoading />
          ) : error && courses.length === 0 ? (
            <WorkspaceUnavailable error={error.message} onRetry={reload} />
          ) : courses.length === 0 ? (
            <NoCourses onRetry={reload} />
          ) : (
            <>
              {outreachMessages.some((item) => item.message.status === "delivered") ? (
                <div className="border-b px-3 py-2 sm:px-6">
                  <Button type="button" variant="outline" className="h-auto w-full justify-between whitespace-normal py-3 text-left" onClick={() => setOutreachOpen(true)}>
                    <span><Bell className="mr-2 inline size-4" aria-hidden="true" />
                      {outreachMessages.filter((item) => item.message.status === "delivered").length} unread Digital Twin check-ins
                    </span>
                    <span className="ml-3 shrink-0 text-xs">Read & reply →</span>
                  </Button>
                </div>
              ) : null}
              {conversation && (evidenceStatus === "loading" || evidenceStatus === "error" || citationsStatus === "loading" || citationsStatus === "error") ? (
                <div className="border-b px-3 py-2 text-xs text-muted-foreground sm:px-6" aria-live="polite">
                  {evidenceStatus === "loading" ? <p>{learnerEvidence ? "Updating learning evidence…" : "Loading learning evidence…"}</p> : null}
                  {evidenceStatus === "error" ? <p>Learning evidence is temporarily unavailable{learnerEvidence ? "; showing the last loaded observations" : ""}. <Button variant="link" size="sm" onClick={() => void retryEvidence()}>Retry evidence</Button></p> : null}
                  {citationsStatus === "loading" ? <p>Loading saved sources…</p> : null}
                  {citationsStatus === "error" ? <p>Some saved sources are unavailable. <Button variant="link" size="sm" onClick={() => void retryCitations()}>Retry sources</Button></p> : null}
                </div>
              ) : null}
              <Conversation
                replyingToCheckIn={Boolean(outreachReply)}
                course={activeCourse}
                messages={messages}
                citationsByMessage={citationsByMessage}
                selectedCitation={selectedCitation}
                autonomousGoals={autonomousGoals}
                learnerEvidence={learnerEvidence}
                isLoading={isLoadingConversation}
                pendingClarification={pendingClarification}
                isSubmitting={isSubmitting}
                onChooseClarification={chooseClarification}
                onOpenCitation={openCitation}
                onChoosePrompt={setDraft}
              />
              <Composer
                composerRef={composerRef}
                outreachReply={outreachReply}
                onCancelReply={() => {
                  cancelOutreachReply()
                  composerRef.current?.querySelector("textarea")?.focus()
                }}
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
            className="workspace-rail fixed inset-y-0 left-0 z-30 w-[min(88vw,320px)] overflow-hidden shadow-[12px_0_40px_rgba(32,33,35,0.12)] outline-none lg:hidden"
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
              if (focusReplyRef.current) {
                focusReplyRef.current = false
                composerRef.current?.querySelector("textarea")?.focus()
              } else {
                outreachTriggerRef.current?.focus()
              }
            }}
            className="fixed inset-y-0 right-0 z-30 w-[min(94vw,420px)] overflow-y-auto border-l bg-white shadow-[-12px_0_40px_rgba(32,33,35,0.14)] outline-none"
          >
            <OutreachPanel
              messages={outreachMessages}
              goals={autonomousGoals}
              learnerEvidence={learnerEvidence}
              evidenceStatus={evidenceStatus}
              enabled={inAppOutreachEnabled}
              snoozedUntil={outreachSnoozedUntil}
              isLoading={isLoadingOutreach}
              isUpdating={isUpdatingOutreach}
              error={outreachError}
              onClose={() => setOutreachOpen(false)}
              onRefresh={refreshOutreach}
              onEnabledChange={setInAppOutreachEnabled}
              onSnooze={snoozeOutreach}
              onMarkRead={markOutreachRead}
              onDismiss={dismissOutreach}
              canReply={Boolean(conversation) && !isLoadingConversation && !isSubmitting && !requiresNewConversation}
              onReply={(messageId) => {
                replyToOutreach(messageId)
                focusReplyRef.current = true
                setOutreachOpen(false)
              }}
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
    <header className="workspace-header flex min-h-16 items-center justify-between gap-3 pl-3 pr-14 sm:pl-5 xl:pr-56">
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
            {activeCourse?.title ?? "Student Digital Twin"}
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
            <a href="/" aria-label="Open Digital Twin setup">
              Digital Twin setup
            </a>
          </Button>
        ) : null}
        <Button
          ref={outreachTriggerRef}
          type="button"
          variant="ghost"
          size="sm"
          className="relative"
          aria-label={
            unreadOutreachCount > 0
              ? `Open Digital Twin check-ins, ${unreadOutreachCount} unread`
              : "Open Digital Twin check-ins"
          }
          onClick={onOpenOutreach}
        >
          <Bell data-icon="inline-start" />
          <span className="hidden sm:inline">Check-ins</span>
          {unreadOutreachCount > 0 ? (
            <span className="absolute top-0.5 right-0.5 flex min-w-5 items-center justify-center rounded-full bg-[var(--accent-strong)] px-1 text-xs leading-5 font-bold text-white">
              {unreadOutreachCount > 9 ? "9+" : unreadOutreachCount}
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
  goals,
  learnerEvidence,
  evidenceStatus,
  enabled,
  snoozedUntil,
  isLoading,
  isUpdating,
  error,
  onClose,
  onRefresh,
  onEnabledChange,
  onSnooze,
  onMarkRead,
  onDismiss,
  onReply,
  canReply,
}: {
  messages: StudentProactiveMessageView[]
  goals: AutonomousGoalV1[]
  learnerEvidence: StudentLearnerEvidence | null
  evidenceStatus: "idle" | "loading" | "ready" | "error"
  enabled: boolean
  snoozedUntil: string | null
  isLoading: boolean
  isUpdating: boolean
  error: string | null
  onClose: () => void
  onRefresh: () => Promise<void>
  onEnabledChange: (enabled: boolean) => Promise<void>
  onSnooze: (days: number | null) => Promise<void>
  onMarkRead: (messageId: string) => Promise<void>
  onDismiss: (messageId: string) => Promise<void>
  onReply: (messageId: string) => void
  canReply: boolean
}) {
  const [section, setSection] = useState<"inbox" | "goals" | "settings">("inbox")
  const activeGoals = goals.filter((goal) => goal.status === "active")
  const pastGoals = goals.filter((goal) => goal.status !== "active")
  const snoozeDate = snoozedUntil ? new Date(snoozedUntil) : null
  const isSnoozed = Boolean(
    snoozeDate && !Number.isNaN(snoozeDate.getTime()) && snoozeDate > new Date(),
  )
  return (
    <>
      <div className="flex min-h-14 items-center justify-between gap-3 border-b pl-5 pr-14">
        <div className="min-w-0">
          <DialogPrimitive.Title className="text-sm font-semibold">
            Digital Twin check-ins
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-0.5 text-xs text-muted-foreground">
            Private messages initiated by your course Digital Twin
          </DialogPrimitive.Description>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Close Digital Twin check-ins"
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </div>

      <nav aria-label="Check-in sections" className="sticky top-0 z-10 flex gap-2 border-b bg-white px-4 py-3">
        {([["inbox", "Inbox"], ["goals", `Goals (${activeGoals.length} active)`], ["settings", "Settings"]] as const).map(([value, label]) => (
          <Button key={value} type="button" variant={section === value ? "secondary" : "ghost"} size="sm" aria-pressed={section === value} onClick={(event) => {
            setSection(value)
            event.currentTarget.closest('[role="dialog"]')?.scrollTo({ top: 0 })
          }}>{label}</Button>
        ))}
      </nav>
      {error ? (
        <Alert variant="destructive" className="mx-4 mt-3 w-auto" role="alert">
          <AlertCircle aria-hidden="true" />
          <AlertTitle>Check-in action unavailable</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {section === "inbox" ? (<>
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

          <div className="px-4 pb-5">
            {isLoading && messages.length === 0 ? (
              <div className="space-y-3" aria-label="Loading Digital Twin check-ins">
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
                    ? "When your professor-approved Digital Twin schedules a useful review, it will appear here."
                    : "Open Settings to allow occasional study follow-ups from your Digital Twin."}
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
                        className="shrink-0 text-xs text-muted-foreground"
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
                    <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
                      <Button
                        type="button"
                        size="sm"
                        disabled={!canReply}
                        onClick={() => onReply(message.id)}
                      >
                        Reply in chat
                      </Button>
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
      </>) : section === "goals" ? (<>
          <div className="border-b px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                My learning goals
              </h2>
              <span className="text-xs text-muted-foreground">
                {activeGoals.length} active
              </span>
            </div>
            {activeGoals.length ? (
              <ul className="mt-3 space-y-2">
                {activeGoals.map((goal) => (
                  <li key={goal.goal_id} className="rounded-lg border bg-white p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="min-w-0 break-words text-sm font-medium leading-6">{goal.approved_course_objective}</p>
                      <span className="shrink-0 rounded-full bg-[var(--subtle)] px-2 py-0.5 text-xs font-medium text-muted-foreground">
                        {goal.status}
                      </span>
                    </div>
                    <details className="mt-2 text-xs leading-5 text-muted-foreground">
                      <summary className="cursor-pointer">Practice details</summary>
                      {goal.learner_subgoal !== goal.approved_course_objective && <p className="mt-2 break-words">{goal.learner_subgoal}</p>}
                      <p className="mt-1 break-words">Goal description: {goal.success_condition}</p>
                      <p className="mt-1">Available until {new Date(goal.expires_at).toLocaleDateString()}.</p>
                    </details>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                No active goal. Your Digital Twin can create a bounded goal only from a professor-approved course objective.
              </p>
            )}
          </div>

          {pastGoals.length ? (
            <details className="border-b px-5 py-4">
              <summary className="cursor-pointer text-sm font-medium">Past goals ({pastGoals.length})</summary>
              <ul className="mt-3 space-y-3">
                {pastGoals.map((goal) => <li key={goal.goal_id} className="rounded-lg border p-3">
                  <p className="break-words text-sm">{goal.approved_course_objective}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Status: {goal.status}</p>
                </li>)}
              </ul>
            </details>
          ) : null}
          <LearnerEvidenceSection evidence={learnerEvidence} status={evidenceStatus} />

      </>) : (<>
          <div className="border-b bg-[var(--shell)] p-4">
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border bg-white p-3.5">
              <Checkbox
                checked={enabled}
                disabled={isUpdating}
                aria-label="Allow private Digital Twin check-ins"
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
              Only private in-app delivery is enabled. Individual learning details
              are never posted to a shared channel.
            </p>
            {enabled ? (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white px-3 py-2.5">
                <p className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                  <Clock3 className="size-3.5 shrink-0" aria-hidden="true" />
                  {isSnoozed && snoozeDate
                    ? `Paused until ${formatOutreachTime(snoozeDate.toISOString())}`
                    : "Quiet hours are respected automatically."}
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isUpdating}
                  onClick={() => void onSnooze(isSnoozed ? null : 7)}
                >
                  {isSnoozed ? "Resume now" : "Pause for 7 days"}
                </Button>
              </div>
            ) : null}
          </div>

      </>)}
    </>
  )
}

function LearnerEvidenceSection({
  evidence,
  status,
}: {
  evidence: StudentLearnerEvidence | null
  status: "idle" | "loading" | "ready" | "error"
}) {
  const belief = evidence?.belief_state
  return (
    <section className="border-b px-5 py-4" aria-labelledby="learning-evidence-heading">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2
            id="learning-evidence-heading"
            className="text-xs font-semibold tracking-wide text-muted-foreground uppercase"
          >
            Observed learning evidence
          </h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            These are observations, not a final mastery score.
            {status === "loading" && evidence ? " Updating observations…" : ""}
            {status === "error" && evidence ? " Refresh unavailable; showing last loaded observations." : ""}
          </p>
        </div>
        {belief ? (
          <span className="shrink-0 text-xs text-muted-foreground">
            Rev. {belief.revision}
          </span>
        ) : null}
      </div>
      {belief?.concepts.length ? (
        <ul className="mt-3 divide-y rounded-lg border">
          {belief.concepts.slice(0, 4).map((concept) => (
            <li key={concept.concept_id} className="px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium">{formatLabel(concept.concept_id)}</p>
                <span className="text-xs text-muted-foreground">
                  {Math.round(concept.uncertainty * 100)}% uncertainty
                </span>
              </div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {concept.observation_count} observations · {concept.assessed_evidence_count} assessed · {concept.correct_evidence_count} correct · {concept.partial_evidence_count} partial · {concept.incorrect_evidence_count} incorrect
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-lg bg-[var(--shell)] px-3 py-2.5 text-xs leading-5 text-muted-foreground">
          {status === "loading" ? "Loading learning evidence…" : status === "error" ? "Learning evidence is temporarily unavailable." : "No assessed learning evidence has been recorded in this conversation yet."}
        </p>
      )}
      {belief ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Last updated {formatOutreachTime(belief.updated_at)}
        </p>
      ) : null}
    </section>
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

function formatLabel(value: string): string {
  const label = value.replaceAll("_", " ").replaceAll("-", " ")
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
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
    <aside className={cn("workspace-rail min-h-0 flex-col", className)}>
      <WorkspaceBrand className="pr-14 lg:pr-4" />
      <div className="p-3 pt-4">
        <h2 className="px-2 pb-2 text-xs font-semibold text-muted-foreground">
          Current course
        </h2>
        <div className="flex flex-col gap-1">
          {isLoading ? (
            <div className="h-16 animate-pulse rounded-xl bg-[var(--subtle)]" />
          ) : (
            courses.map((course) => (
              <button
                key={course.course_id}
                type="button"
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl px-2.5 py-2.5 text-left outline-none transition-colors hover:bg-white/80 focus-visible:ring-2 focus-visible:ring-ring/30",
                  activeCourse?.course_id === course.course_id &&
                    "bg-white shadow-[0_1px_2px_rgba(25,25,29,0.06),0_5px_14px_rgba(25,25,29,0.04)]",
                )}
                aria-pressed={activeCourse?.course_id === course.course_id}
                disabled={isStartingConversation || isSubmitting}
                onClick={() => void onSelectCourse(course.course_id)}
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
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
          <div className="flex items-center gap-2 rounded-lg bg-white/70 px-2.5 py-2 text-sm text-foreground">
            <MessageCircle className="size-4 shrink-0 text-[var(--accent-strong)]" aria-hidden="true" />
            <span className="truncate">{conversationTitle}</span>
          </div>
        </div>
      ) : null}

      <p className="mt-auto border-t px-4 py-3 text-xs leading-5 text-muted-foreground">
        {SESSION_AUTH_ENABLED
          ? "Course access follows your signed-in account."
          : "Synthetic local account · Conversations are saved for this account."}
      </p>
    </aside>
  )
}

function Conversation({
  replyingToCheckIn,
  course,
  messages,
  citationsByMessage,
  selectedCitation,
  autonomousGoals,
  learnerEvidence,
  isLoading,
  pendingClarification,
  isSubmitting,
  onChooseClarification,
  onOpenCitation,
  onChoosePrompt,
}: {
  replyingToCheckIn: boolean
  course: StudentCourse | null
  messages: StudentChatMessage[]
  citationsByMessage: Record<string, StudentCitation[]>
  selectedCitation: StudentCitation | null
  autonomousGoals: AutonomousGoalV1[]
  learnerEvidence: StudentLearnerEvidence | null
  isLoading: boolean
  pendingClarification: ClarificationRequestV1 | null
  isSubmitting: boolean
  onChooseClarification: (optionId: string) => Promise<void>
  onOpenCitation: (
    messageId: string,
    citationId: string,
    trigger: HTMLButtonElement,
  ) => void
  onChoosePrompt: (prompt: string) => void
}) {
  const hasConversation = messages.length > 0 || Boolean(pendingClarification)

  if (!hasConversation) {
    return (
      <section aria-label="Student tutoring conversation" className="workspace-canvas min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        {isLoading ? <ConversationLoading /> : replyingToCheckIn ? (
          <div className="mx-auto max-w-[840px]">
            <h2 className="text-lg font-semibold">Continue the check-in</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Read your Digital Twin’s message below, then write your reply. Your response will be linked to this check-in.</p>
          </div>
        ) : course ? <TutorWelcome course={course} goals={autonomousGoals} learnerEvidence={learnerEvidence} onChoosePrompt={onChoosePrompt} /> : null}
      </section>
    )
  }

  return (
    <ChatContainerRoot
      aria-label="Student tutoring conversation"
      className="workspace-canvas min-h-0 flex-1"
    >
      <ChatContainerContent
        className="mx-auto w-full max-w-[840px] gap-7 px-4 py-8 sm:px-8 sm:py-10"
      >
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
        {pendingClarification ? (
          <ClarificationOptions
            request={pendingClarification}
            disabled={isSubmitting}
            onChoose={onChooseClarification}
          />
        ) : null}
        <ChatContainerScrollAnchor />
      </ChatContainerContent>
    </ChatContainerRoot>
  )
}

function ClarificationOptions({
  request,
  disabled,
  onChoose,
}: {
  request: ClarificationRequestV1
  disabled: boolean
  onChoose: (optionId: string) => Promise<void>
}) {
  return (
    <section
      className="ml-12 max-w-[70ch] rounded-xl border border-[var(--accent)]/20 bg-[var(--accent-soft)]/45 p-3.5"
      aria-labelledby={`clarification-${request.request_id}`}
    >
      <h3
        id={`clarification-${request.request_id}`}
        className="text-sm font-semibold text-foreground"
      >
        Choose the meaning you intended
      </h3>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        The Digital Twin will use only the selected approved source passage.
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {request.options.map((option, index) => (
          <button
            key={option.option_id}
            type="button"
            disabled={disabled}
            className="flex min-h-11 w-full items-start gap-3 rounded-lg border bg-white px-3 py-2.5 text-left text-sm leading-5 outline-none transition-colors hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] focus-visible:ring-2 focus-visible:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => void onChoose(option.option_id)}
          >
            <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent-strong)]">
              {index + 1}
            </span>
            <span>{option.label}</span>
          </button>
        ))}
      </div>
    </section>
  )
}

function TutorWelcome({
  course,
  goals,
  learnerEvidence,
  onChoosePrompt,
}: {
  course: StudentCourse
  goals: AutonomousGoalV1[]
  learnerEvidence: StudentLearnerEvidence | null
  onChoosePrompt: (prompt: string) => void
}) {
  const activeGoal = goals.find((goal) => goal.status === "active")
  const observedConceptCount = learnerEvidence?.belief_state?.concepts.length ?? 0
  const suggestions = [
    activeGoal
      ? `Help me continue this learning goal: ${activeGoal.learner_subgoal}`
      : "Explain a key concept from this course",
    "Quiz me using the approved course material",
    "Help me work through something I misunderstood",
  ]

  return (
    <section className="mx-auto w-full max-w-2xl" aria-labelledby="tutor-welcome-title">
      <div className="flex items-center gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-[var(--ink)] text-white shadow-[0_8px_22px_rgba(25,25,29,0.18)]">
          <Sparkles className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="workspace-kicker">Your course Digital Twin</p>
          <h2
            id="tutor-welcome-title"
            className="mt-0.5 text-balance text-2xl font-semibold tracking-[-0.03em] sm:text-3xl"
          >
            Study with your course Digital Twin
          </h2>
        </div>
      </div>

      <p className="mt-5 max-w-[65ch] text-sm leading-6 text-muted-foreground sm:text-base sm:leading-7">
        Ask a question about {course.title}, or reply to a Digital Twin check-in.
        Responses use the professor-approved materials for this course.
      </p>

      <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-y py-3 text-xs font-medium text-[var(--ink-soft)]">
        <span className="inline-flex items-center gap-1.5">
          <FileCheck2 className="size-3.5 text-[var(--success)]" aria-hidden="true" />
          Approved sources only
        </span>
        <span className="inline-flex items-center gap-1.5">
          <BookOpen className="size-3.5 text-[var(--accent-strong)]" aria-hidden="true" />
          Inspectable citations
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Target className="size-3.5 text-[var(--accent-strong)]" aria-hidden="true" />
          {activeGoal
            ? "Active learning goal"
            : observedConceptCount > 0
              ? `${observedConceptCount} observed concept${observedConceptCount === 1 ? "" : "s"}`
              : "Learning evidence appears as you participate"}
        </span>
      </div>

      {activeGoal ? (
        <div className="mt-5 rounded-xl bg-[var(--accent-soft)] px-4 py-3.5">
          <p className="text-xs font-semibold text-[var(--accent-strong)]">
            Current learning focus
          </p>
          <p className="mt-1 text-sm font-medium leading-6">
            {activeGoal.approved_course_objective}
          </p>
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-2" aria-label="Suggested questions">
        <p className="workspace-kicker px-1">Try asking</p>
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion}
            type="button"
            className="group flex min-h-11 w-full items-center justify-between gap-4 rounded-xl border bg-white px-4 py-3 text-left text-sm font-medium shadow-[0_1px_2px_rgba(25,25,29,0.03)] outline-none transition-[border-color,background-color,transform] hover:-translate-y-px hover:border-[var(--accent-border)] hover:bg-[var(--accent-soft)]/35 focus-visible:ring-2 focus-visible:ring-ring/35"
            onClick={() => onChoosePrompt(suggestion)}
          >
            <span>{index === 0 && activeGoal ? "Work on my current learning goal" : suggestion}</span>
            <ArrowUpRight className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-[var(--accent-strong)]" aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
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
    <article className={cn("flex gap-3.5", !isTutor && "justify-end")}>
      {isTutor ? (
        <TutorAvatar />
      ) : (
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--subtle)] text-muted-foreground">
          <UserRound className="size-4.5" aria-hidden="true" />
        </span>
      )}
      <div
        className={cn(
          "min-w-0 max-w-[70ch] pt-0.5",
          !isTutor && "order-first rounded-2xl bg-[var(--subtle)] px-4 py-3",
        )}
      >
        <h2 className="text-sm font-semibold">{isTutor ? "Digital Twin" : "You"}</h2>
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
  composerRef,
  outreachReply,
  onCancelReply,
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
  composerRef: RefObject<HTMLDivElement | null>
  outreachReply: StudentProactiveMessageView | null
  onCancelReply: () => void
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
    <div ref={composerRef} className="workspace-canvas shrink-0 px-3 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 sm:px-6">
      <div className="mx-auto w-full max-w-[840px]">
        {error ? (
          <Alert variant="destructive" className="mb-3">
            <AlertCircle />
            <AlertTitle>
              {requiresNewConversation
                ? "This course release changed"
                : errorScope === "workspace"
                  ? "Course conversation unavailable"
                  : "The reply was not confirmed"}
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
        {outreachReply ? (
          <section aria-label="Replying to Digital Twin check-in" className="mb-2 rounded-xl border border-[var(--accent-border)] bg-[var(--accent-soft)]/30 p-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Replying to your Digital Twin</h2>
              <Button type="button" variant="ghost" size="sm" disabled={isSubmitting} onClick={onCancelReply}>Cancel reply</Button>
            </div>
            <div tabIndex={0} aria-label="Original check-in" className="mt-2 max-h-[24dvh] overflow-y-auto break-words rounded-md focus-visible:outline-2 focus-visible:outline-ring">
              <p className="whitespace-pre-line text-sm leading-6">{outreachReply.message.content}</p>
            </div>
            {outreachReply.citations.length ? <div className="mt-2 max-h-16 overflow-y-auto text-xs leading-5 text-muted-foreground">
              {outreachReply.citations.map((citation) => <p key={citation.id}>Source: {citation.title} · {citation.locator}</p>)}
            </div> : null}
          </section>
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
            placeholder={isLoading ? "Opening the course conversation…" : outreachReply ? "Write your reply to this check-in…" : "Ask about this course"}
            aria-label={outreachReply ? "Reply to Digital Twin check-in" : "Ask about this course"}
            maxLength={8000}
            className="min-h-12 px-2 py-2.5 text-sm"
          />
          <PromptInputActions className="justify-end px-1 pb-1">
            <PromptInputAction tooltip={outreachReply ? "Send reply" : "Send question"}>
              <Button
                type="button"
                size="icon-lg"
                className="size-11 sm:size-9"
                aria-label={outreachReply ? "Send reply" : "Send question"}
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
      {/* The fixed account control occupies the desktop top-right corner. */}
      <div className={cn("flex min-h-14 items-center justify-between gap-3 border-b px-5", !dialogTitle && "pr-16")}>
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

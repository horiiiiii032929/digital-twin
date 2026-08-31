import { useCallback, useEffect, useRef, useState } from "react"

import {
  STUDENT_ACCOUNT_ID,
  StudentApiError,
  createStudentConversation,
  getStudentConversation,
  dismissStudentOutreach,
  listStudentAutonomousGoals,
  listStudentOutreach,
  listStudentOutreachPreferences,
  listStudentCourses,
  listStudentMessageCitations,
  markStudentOutreachRead,
  submitStudentMessage,
  updateStudentInAppOutreachPreference,
} from "@/lib/api"
import type {
  AutonomousGoalV1,
  StudentChatMessage,
  StudentCitation,
  StudentConversation,
  StudentCourse,
  StudentOutreachPreference,
  StudentProactiveMessageView,
} from "@/lib/api"
import {
  forgetStudentConversation,
  isConversationForCurrentRelease,
  readStudentConversationIndex,
  rememberStudentConversation,
  writeStudentConversationIndex,
} from "@/lib/student/conversation-index"
import { createStudentRequestId } from "@/lib/student/request-id"

export type StudentWorkspaceError = {
  message: string
  code?: string
  status?: number
  scope: "workspace" | "message"
}

export type StudentWorkspaceController = {
  accountId: string
  courses: StudentCourse[]
  activeCourse: StudentCourse | null
  conversation: StudentConversation | null
  messages: StudentChatMessage[]
  citationsByMessage: Record<string, StudentCitation[]>
  selectedCitation: StudentCitation | null
  draft: string
  error: StudentWorkspaceError | null
  isLoadingCourses: boolean
  isLoadingConversation: boolean
  isSubmitting: boolean
  outreachMessages: StudentProactiveMessageView[]
  autonomousGoals: AutonomousGoalV1[]
  inAppOutreachEnabled: boolean
  outreachSnoozedUntil: string | null
  isLoadingOutreach: boolean
  isUpdatingOutreach: boolean
  outreachError: string | null
  requiresNewConversation: boolean
  setDraft: (value: string) => void
  reload: () => Promise<void>
  selectCourse: (courseId: string) => Promise<void>
  startNewConversation: () => Promise<void>
  startCurrentRelease: () => Promise<void>
  sendMessage: () => Promise<void>
  refreshOutreach: () => Promise<void>
  setInAppOutreachEnabled: (enabled: boolean) => Promise<void>
  snoozeOutreach: (days: number | null) => Promise<void>
  markOutreachRead: (messageId: string) => Promise<void>
  dismissOutreach: (messageId: string) => Promise<void>
  replyToOutreach: (messageId: string) => void
  selectCitation: (messageId: string, citationId: string) => void
}

type PendingRequest = {
  content: string
  requestId: string
  respondingToOutreachMessageId?: string
}

export function useStudentWorkspace(
  accountId = STUDENT_ACCOUNT_ID,
): StudentWorkspaceController {
  const [courses, setCourses] = useState<StudentCourse[]>([])
  const [activeCourse, setActiveCourse] = useState<StudentCourse | null>(null)
  const [conversation, setConversation] =
    useState<StudentConversation | null>(null)
  const [messages, setMessages] = useState<StudentChatMessage[]>([])
  const [citationsByMessage, setCitationsByMessage] = useState<
    Record<string, StudentCitation[]>
  >({})
  const [selectedCitation, setSelectedCitation] =
    useState<StudentCitation | null>(null)
  const [draft, setDraft] = useState("")
  const [error, setError] = useState<StudentWorkspaceError | null>(null)
  const [isLoadingCourses, setIsLoadingCourses] = useState(true)
  const [isLoadingConversation, setIsLoadingConversation] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [outreachMessages, setOutreachMessages] = useState<
    StudentProactiveMessageView[]
  >([])
  const [autonomousGoals, setAutonomousGoals] = useState<AutonomousGoalV1[]>([])
  const [outreachPreferences, setOutreachPreferences] = useState<
    StudentOutreachPreference[]
  >([])
  const [isLoadingOutreach, setIsLoadingOutreach] = useState(false)
  const [isUpdatingOutreach, setIsUpdatingOutreach] = useState(false)
  const [outreachError, setOutreachError] = useState<string | null>(null)
  const startedRef = useRef(false)
  const operationRef = useRef(0)
  const pendingRequestRef = useRef<PendingRequest | null>(null)
  const outreachReplyRef = useRef<string | null>(null)
  const outreachOperationRef = useRef(0)
  const indexRef = useRef(
    typeof window === "undefined"
      ? {
          version: 1 as const,
          activeCourseId: null,
          conversationByCourse: {},
        }
      : readStudentConversationIndex(window.localStorage, accountId),
  )

  const saveIndex = useCallback(
    (next: typeof indexRef.current) => {
      indexRef.current = next
      if (typeof window !== "undefined") {
        try {
          writeStudentConversationIndex(window.localStorage, next, accountId)
        } catch {
          // Browser storage is an optional convenience; server state stays authoritative.
        }
      }
    },
    [accountId],
  )

  const loadConversation = useCallback(
    async (course: StudentCourse, conversationId?: string) => {
      const operation = ++operationRef.current
      setActiveCourse(course)
      setConversation(null)
      setMessages([])
      setCitationsByMessage({})
      setSelectedCitation(null)
      setError(null)
      setIsLoadingConversation(true)
      pendingRequestRef.current = null

      let activeConversationId = conversationId
      if (activeConversationId) {
        try {
          const view = await getStudentConversation(
            activeConversationId,
            accountId,
          )
          if (!isConversationForCurrentRelease(view.conversation, course)) {
            saveIndex(
              forgetStudentConversation(indexRef.current, course.course_id),
            )
            activeConversationId = undefined
          } else {
            const tutorMessages = view.messages.filter(
              (message) => message.role === "tutor",
            )
            const citationLists = await Promise.all(
              tutorMessages.map((message) =>
                listStudentMessageCitations(message.id, accountId),
              ),
            )
            if (operation !== operationRef.current) return

            const nextCitations = Object.fromEntries(
              tutorMessages.map((message, index) => [
                message.id,
                citationLists[index] ?? [],
              ]),
            )
            const latestCitation = [...citationLists]
              .reverse()
              .find((citations) => citations.length > 0)?.[0]
            setConversation(view.conversation)
            setMessages(view.messages)
            setCitationsByMessage(nextCitations)
            setSelectedCitation(latestCitation ?? null)
            setIsLoadingConversation(false)
            return
          }
        } catch (caught) {
          const staleLocalReference =
            caught instanceof StudentApiError && [403, 404].includes(caught.status)
          if (!staleLocalReference) {
            if (operation === operationRef.current) {
              setError(toWorkspaceError(caught, "workspace"))
              setIsLoadingConversation(false)
            }
            return
          }
          saveIndex(forgetStudentConversation(indexRef.current, course.course_id))
          activeConversationId = undefined
        }
      }

      try {
        const created = await createStudentConversation(course.course_id, accountId)
        if (operation !== operationRef.current) return
        saveIndex(
          rememberStudentConversation(
            indexRef.current,
            course.course_id,
            created.id,
          ),
        )
        setConversation(created)
        setIsLoadingConversation(false)
      } catch (caught) {
        if (operation !== operationRef.current) return
        setError(toWorkspaceError(caught, "workspace"))
        setIsLoadingConversation(false)
      }
    },
    [accountId, saveIndex],
  )

  const reload = useCallback(async () => {
    const operation = ++operationRef.current
    setIsLoadingCourses(true)
    setError(null)
    try {
      const availableCourses = await listStudentCourses(accountId)
      if (operation !== operationRef.current) return
      setCourses(availableCourses)
      setIsLoadingCourses(false)

      if (availableCourses.length === 0) {
        setActiveCourse(null)
        setConversation(null)
        setMessages([])
        setCitationsByMessage({})
        setSelectedCitation(null)
        return
      }

      const rememberedCourse = availableCourses.find(
        (course) => course.course_id === indexRef.current.activeCourseId,
      )
      const course = rememberedCourse ?? availableCourses[0]
      saveIndex({ ...indexRef.current, activeCourseId: course.course_id })
      await loadConversation(
        course,
        indexRef.current.conversationByCourse[course.course_id],
      )
    } catch (caught) {
      if (operation !== operationRef.current) return
      setError(toWorkspaceError(caught, "workspace"))
      setIsLoadingCourses(false)
    }
  }, [accountId, loadConversation, saveIndex])

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    void reload()
  }, [reload])

  const loadOutreach = useCallback(
    async (courseId: string, silent = false) => {
      const operation = ++outreachOperationRef.current
      if (!silent) setIsLoadingOutreach(true)
      setOutreachError(null)
      try {
        const [nextMessages, nextPreferences, nextGoals] = await Promise.all([
          listStudentOutreach(courseId, accountId),
          listStudentOutreachPreferences(courseId, accountId),
          listStudentAutonomousGoals(courseId, accountId),
        ])
        if (operation !== outreachOperationRef.current) return
        setOutreachMessages(nextMessages)
        setOutreachPreferences(nextPreferences)
        setAutonomousGoals(nextGoals)
      } catch (caught) {
        if (operation !== outreachOperationRef.current) return
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      } finally {
        if (operation === outreachOperationRef.current) {
          setIsLoadingOutreach(false)
        }
      }
    },
    [accountId],
  )

  useEffect(() => {
    const courseId = activeCourse?.course_id
    if (!courseId) {
      setOutreachMessages([])
      setOutreachPreferences([])
      setAutonomousGoals([])
      return
    }
    void loadOutreach(courseId)
    const interval = window.setInterval(() => {
      void loadOutreach(courseId, true)
    }, 30_000)
    return () => window.clearInterval(interval)
  }, [activeCourse?.course_id, loadOutreach])

  const selectCourse = useCallback(
    async (courseId: string) => {
      if (isSubmitting) return
      const course = courses.find((entry) => entry.course_id === courseId)
      if (!course || course.course_id === activeCourse?.course_id) return
      saveIndex({ ...indexRef.current, activeCourseId: course.course_id })
      await loadConversation(
        course,
        indexRef.current.conversationByCourse[course.course_id],
      )
    },
    [
      activeCourse?.course_id,
      courses,
      isSubmitting,
      loadConversation,
      saveIndex,
    ],
  )

  const startNewConversation = useCallback(async () => {
    if (!activeCourse || isSubmitting) return
    saveIndex(forgetStudentConversation(indexRef.current, activeCourse.course_id))
    await loadConversation(activeCourse)
  }, [activeCourse, isSubmitting, loadConversation, saveIndex])

  const startCurrentRelease = useCallback(async () => {
    if (!activeCourse) return

    const courseId = activeCourse.course_id
    const operation = ++operationRef.current
    setIsLoadingConversation(true)
    setError(null)

    try {
      const availableCourses = await listStudentCourses(accountId)
      if (operation !== operationRef.current) return

      const currentCourse = availableCourses.find(
        (course) => course.course_id === courseId,
      )
      if (!currentCourse) {
        setError({
          message: "No current published release is available for this course.",
          code: "release_unavailable",
          scope: "message",
        })
        setIsLoadingConversation(false)
        return
      }

      setCourses(availableCourses)
      saveIndex(forgetStudentConversation(indexRef.current, courseId))
      await loadConversation(currentCourse)
    } catch (caught) {
      if (operation !== operationRef.current) return
      setError({
        ...toWorkspaceError(caught, "message"),
        code: "release_unavailable",
      })
      setIsLoadingConversation(false)
    }
  }, [accountId, activeCourse, loadConversation, saveIndex])

  const sendMessage = useCallback(async () => {
    const content = draft.trim()
    if (!content || !conversation || isSubmitting) return

    const pending = pendingRequestRef.current
    const request =
      pending?.content === content
        ? pending
        : {
            content,
            requestId: createStudentRequestId(),
            ...(outreachReplyRef.current
              ? { respondingToOutreachMessageId: outreachReplyRef.current }
              : {}),
          }
    pendingRequestRef.current = request
    const operation = operationRef.current
    setIsSubmitting(true)
    setError(null)

    try {
      const turn = await submitStudentMessage(
        conversation.id,
        content,
        request.requestId,
        accountId,
        request.respondingToOutreachMessageId,
      )
      if (operation !== operationRef.current) return
      setMessages((current) =>
        appendUniqueMessages(current, [turn.student_message, turn.tutor_message]),
      )
      setCitationsByMessage((current) => ({
        ...current,
        [turn.tutor_message.id]: turn.citations,
      }))
      setSelectedCitation(turn.citations[0] ?? null)
      setDraft("")
      outreachReplyRef.current = null
      pendingRequestRef.current = null
    } catch (caught) {
      if (operation !== operationRef.current) return
      setError(toWorkspaceError(caught, "message"))
    } finally {
      setIsSubmitting(false)
    }
  }, [accountId, conversation, draft, isSubmitting])

  const selectCitation = useCallback(
    (messageId: string, citationId: string) => {
      const citation = citationsByMessage[messageId]?.find(
        (entry) => entry.id === citationId,
      )
      if (citation) setSelectedCitation(citation)
    },
    [citationsByMessage],
  )

  const refreshOutreach = useCallback(async () => {
    if (!activeCourse) return
    await loadOutreach(activeCourse.course_id)
  }, [activeCourse, loadOutreach])

  const setInAppOutreachEnabled = useCallback(
    async (enabled: boolean) => {
      if (!activeCourse || isUpdatingOutreach) return
      setIsUpdatingOutreach(true)
      setOutreachError(null)
      try {
        const preference = await updateStudentInAppOutreachPreference(
          activeCourse.course_id,
          enabled,
          accountId,
        )
        setOutreachPreferences((current) => [
          ...current.filter((item) => item.channel !== "in-app"),
          preference,
        ])
      } catch (caught) {
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      } finally {
        setIsUpdatingOutreach(false)
      }
    },
    [accountId, activeCourse, isUpdatingOutreach],
  )

  const snoozeOutreach = useCallback(
    async (days: number | null) => {
      if (!activeCourse || isUpdatingOutreach || (days !== null && days < 1)) return
      setIsUpdatingOutreach(true)
      setOutreachError(null)
      try {
        const until = days === null
          ? null
          : new Date(Date.now() + days * 24 * 60 * 60 * 1_000).toISOString()
        const preference = await updateStudentInAppOutreachPreference(
          activeCourse.course_id,
          true,
          accountId,
          until,
        )
        setOutreachPreferences((current) => [
          ...current.filter((item) => item.channel !== "in-app"),
          preference,
        ])
      } catch (caught) {
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      } finally {
        setIsUpdatingOutreach(false)
      }
    },
    [accountId, activeCourse, isUpdatingOutreach],
  )

  const markOutreachRead = useCallback(
    async (messageId: string) => {
      try {
        const updated = await markStudentOutreachRead(messageId, accountId)
        setOutreachMessages((current) =>
          current.map((item) =>
            item.message.id === messageId ? updated : item,
          ),
        )
      } catch (caught) {
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      }
    },
    [accountId],
  )

  const dismissOutreach = useCallback(
    async (messageId: string) => {
      try {
        await dismissStudentOutreach(messageId, accountId)
        setOutreachMessages((current) =>
          current.filter((item) => item.message.id !== messageId),
        )
      } catch (caught) {
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      }
    },
    [accountId],
  )

  const replyToOutreach = useCallback((messageId: string) => {
    outreachReplyRef.current = messageId
    pendingRequestRef.current = null
    setDraft("My response to this check-in: ")
  }, [])

  return {
    accountId,
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
    autonomousGoals,
    inAppOutreachEnabled:
      outreachPreferences.find((item) => item.channel === "in-app")?.enabled ??
      false,
    outreachSnoozedUntil:
      outreachPreferences.find((item) => item.channel === "in-app")
        ?.snoozed_until ?? null,
    isLoadingOutreach,
    isUpdatingOutreach,
    outreachError,
    requiresNewConversation:
      error?.code === "release_unavailable" || error?.code === "profile_mismatch",
    setDraft,
    reload,
    selectCourse,
    startNewConversation,
    startCurrentRelease,
    sendMessage,
    refreshOutreach,
    setInAppOutreachEnabled,
    snoozeOutreach,
    markOutreachRead,
    dismissOutreach,
    replyToOutreach,
    selectCitation,
  }
}

function appendUniqueMessages(
  current: StudentChatMessage[],
  additions: StudentChatMessage[],
): StudentChatMessage[] {
  const existingIds = new Set(current.map((message) => message.id))
  return [
    ...current,
    ...additions.filter((message) => !existingIds.has(message.id)),
  ]
}

function toWorkspaceError(
  caught: unknown,
  scope: StudentWorkspaceError["scope"],
): StudentWorkspaceError {
  if (caught instanceof StudentApiError) {
    return {
      message: caught.message,
      code: caught.code,
      status: caught.status,
      scope,
    }
  }
  return {
    message:
      caught instanceof Error
        ? caught.message
        : "The student workspace could not complete the request.",
    scope,
  }
}

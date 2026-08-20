import { useCallback, useEffect, useRef, useState } from "react"

import {
  STUDENT_ACCOUNT_ID,
  StudentApiError,
  createStudentConversation,
  getStudentConversation,
  listStudentCourses,
  listStudentMessageCitations,
  submitStudentMessage,
} from "@/lib/api"
import type {
  StudentChatMessage,
  StudentCitation,
  StudentConversation,
  StudentCourse,
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
  requiresNewConversation: boolean
  setDraft: (value: string) => void
  reload: () => Promise<void>
  selectCourse: (courseId: string) => Promise<void>
  startNewConversation: () => Promise<void>
  startCurrentRelease: () => Promise<void>
  sendMessage: () => Promise<void>
  selectCitation: (messageId: string, citationId: string) => void
}

type PendingRequest = {
  content: string
  requestId: string
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
  const startedRef = useRef(false)
  const operationRef = useRef(0)
  const pendingRequestRef = useRef<PendingRequest | null>(null)
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
        : { content, requestId: createStudentRequestId() }
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
    requiresNewConversation:
      error?.code === "release_unavailable" || error?.code === "profile_mismatch",
    setDraft,
    reload,
    selectCourse,
    startNewConversation,
    startCurrentRelease,
    sendMessage,
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

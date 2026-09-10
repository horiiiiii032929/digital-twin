import { useCallback, useEffect, useRef, useState } from "react"

import {
  STUDENT_ACCOUNT_ID,
  StudentApiError,
  createStudentConversation,
  getStudentConversation,
  getStudentLearnerEvidence,
  dismissStudentOutreach,
  listStudentAutonomousGoals,
  listStudentOutreach,
  listStudentOutreachPreferences,
  listStudentCourses,
  listStudentConversations,
  listStudentMessageCitations,
  markStudentOutreachRead,
  submitStudentMessage,
  updateStudentInAppOutreachPreference,
} from "@/lib/api"
import type {
  AutonomousGoalV1,
  ClarificationRequestV1,
  StudentChatMessage,
  StudentCitation,
  StudentConversation,
  StudentCourse,
  StudentOutreachPreference,
  StudentProactiveMessageView,
  StudentLearnerEvidence,
} from "@/lib/api"
import {
  forgetStudentConversation,
  isConversationForCurrentRelease,
  readStudentConversationIndex,
  rememberStudentConversation,
  writeStudentConversationIndex,
} from "@/lib/student/conversation-index"
import { createStudentRequestId } from "@/lib/student/request-id"
import { readPendingStudentRequest, savePendingStudentRequest } from "@/lib/student/pending-request"

export type MetadataStatus = "idle" | "loading" | "ready" | "error"

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
  conversationHistory: StudentConversation[]
  messages: StudentChatMessage[]
  citationsByMessage: Record<string, StudentCitation[]>
  selectedCitation: StudentCitation | null
  draft: string
  error: StudentWorkspaceError | null
  isLoadingCourses: boolean
  isLoadingConversation: boolean
  isSubmitting: boolean
  outreachMessages: StudentProactiveMessageView[]
  outreachReply: StudentProactiveMessageView | null
  autonomousGoals: AutonomousGoalV1[]
  learnerEvidence: StudentLearnerEvidence | null
  evidenceStatus: MetadataStatus
  citationsStatus: MetadataStatus
  retryEvidence: () => Promise<void>
  retryCitations: () => Promise<void>
  pendingClarification: ClarificationRequestV1 | null
  inAppOutreachEnabled: boolean
  outreachSnoozedUntil: string | null
  isLoadingOutreach: boolean
  isUpdatingOutreach: boolean
  outreachError: string | null
  requiresNewConversation: boolean
  setDraft: (value: string) => void
  reload: () => Promise<void>
  selectCourse: (courseId: string) => Promise<void>
  selectConversation: (conversationId: string) => Promise<void>
  startNewConversation: () => Promise<void>
  startCurrentRelease: () => Promise<void>
  sendMessage: () => Promise<void>
  chooseClarification: (optionId: string) => Promise<void>
  refreshOutreach: () => Promise<void>
  setInAppOutreachEnabled: (enabled: boolean) => Promise<void>
  snoozeOutreach: (days: number | null) => Promise<void>
  markOutreachRead: (messageId: string) => Promise<void>
  dismissOutreach: (messageId: string) => Promise<void>
  replyToOutreach: (messageId: string) => void
  cancelOutreachReply: () => void
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
  const [conversationHistory, setConversationHistory] = useState<StudentConversation[]>([])
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
  const [outreachReply, setOutreachReply] = useState<StudentProactiveMessageView | null>(null)
  const [autonomousGoals, setAutonomousGoals] = useState<AutonomousGoalV1[]>([])
  const [learnerEvidence, setLearnerEvidence] =
    useState<StudentLearnerEvidence | null>(null)
  const [pendingClarification, setPendingClarification] =
    useState<ClarificationRequestV1 | null>(null)
  const [outreachPreferences, setOutreachPreferences] = useState<
    StudentOutreachPreference[]
  >([])
  const [isLoadingOutreach, setIsLoadingOutreach] = useState(false)
  const [isUpdatingOutreach, setIsUpdatingOutreach] = useState(false)
  const [outreachError, setOutreachError] = useState<string | null>(null)
  const [evidenceStatus, setEvidenceStatus] = useState<MetadataStatus>("idle")
  const [citationsStatus, setCitationsStatus] = useState<MetadataStatus>("idle")
  const evidenceReadRef = useRef(0)
  const citationReadRef = useRef(0)
  const citationSelectionRef = useRef(0)
  const submitLockRef = useRef(false)
  const startedRef = useRef(false)
  const operationRef = useRef(0)
  const pendingRequestRef = useRef<PendingRequest | null>(null)
  const outreachReplyRef = useRef<string | null>(null)
  const outreachOperationRef = useRef(0)
  const outreachScopeRef = useRef(0)
  const outreachCourseRef = useRef<string | null>(null)
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

  const readEvidence = useCallback(async (conversationId: string, scope: number) => {
    const read = ++evidenceReadRef.current
    setEvidenceStatus("loading")
    try {
      const evidence = await getStudentLearnerEvidence(conversationId, accountId)
      if (scope !== operationRef.current || read !== evidenceReadRef.current) return
      setLearnerEvidence(evidence)
      setEvidenceStatus("ready")
    } catch {
      if (scope === operationRef.current && read === evidenceReadRef.current) setEvidenceStatus("error")
    }
  }, [accountId])

  const readCitations = useCallback(async (history: StudentChatMessage[], scope: number) => {
    const read = ++citationReadRef.current
    const tutors = history.filter(message => message.role === "tutor")
    setCitationsStatus("loading")
    let failed = false
    const selection = citationSelectionRef.current
    const loaded: Record<string, StudentCitation[]> = {}
    let next = 0
    // Optional history reads must leave browser connections for chat and sign-out.
    const loadNext = async () => {
      while (next < tutors.length && scope === operationRef.current && read === citationReadRef.current) {
        const message = tutors[next++]
        try {
          const citations = await listStudentMessageCitations(message.id, accountId)
          if (scope !== operationRef.current || read !== citationReadRef.current) return
          loaded[message.id] = citations
          setCitationsByMessage(current => ({ ...current, [message.id]: current[message.id] ?? citations }))
        } catch {
          failed = true
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(2, tutors.length) }, loadNext))
    if (scope === operationRef.current && read === citationReadRef.current) {
      setCitationsStatus(failed ? "error" : "ready")
      if (selection === citationSelectionRef.current) {
        const latest = [...tutors].reverse().flatMap(message => loaded[message.id] ?? [])[0]
        setSelectedCitation(current => current ?? latest ?? null)
      }
    }
  }, [accountId])

  const retryEvidence = useCallback(async () => {
    if (conversation) await readEvidence(conversation.id, operationRef.current)
  }, [conversation, readEvidence])
  const retryCitations = useCallback(async () => {
    if (conversation) await readCitations(messages, operationRef.current)
  }, [conversation, messages, readCitations])

  const loadConversation = useCallback(
    async (course: StudentCourse, conversationId?: string, forceNew = false) => {
      const operation = ++operationRef.current
      if (outreachCourseRef.current !== course.course_id) {
        setConversationHistory([])
        outreachCourseRef.current = course.course_id
        ++outreachScopeRef.current
        ++outreachOperationRef.current
        setOutreachMessages([])
        setOutreachPreferences([])
        setAutonomousGoals([])
        setOutreachError(null)
        setIsUpdatingOutreach(false)
      }
      ++evidenceReadRef.current
      ++citationReadRef.current
      setEvidenceStatus("idle")
      setCitationsStatus("idle")
      setActiveCourse(course)
      setConversation(null)
      setMessages([])
      setCitationsByMessage({})
      setSelectedCitation(null)
      setLearnerEvidence(null)
      setPendingClarification(null)
      setError(null)
      setIsLoadingConversation(true)
      pendingRequestRef.current = null
      outreachReplyRef.current = null
      setOutreachReply(null)
      setDraft("")

      let resumableIds: string[] = []
      if (!forceNew) {
        try {
          const history = await listStudentConversations(course.course_id, accountId)
          if (operation !== operationRef.current) return
          setConversationHistory(history.filter((item) => isConversationForCurrentRelease(item, course)))
          resumableIds = history.filter((item) =>
            isConversationForCurrentRelease(item, course),
          ).map((item) => item.id)
          if (conversationId && resumableIds.includes(conversationId)) {
            resumableIds = [conversationId, ...resumableIds.filter((id) => id !== conversationId)]
          }
        } catch (caught) {
          if (operation !== operationRef.current) return
          setError(toWorkspaceError(caught, "workspace"))
          setIsLoadingConversation(false)
          return
        }
      }
      for (const activeConversationId of resumableIds) {
        try {
          const view = await getStudentConversation(
            activeConversationId,
            accountId,
          )
          if (operation !== operationRef.current) return
          if (!isConversationForCurrentRelease(view.conversation, course)) {
            saveIndex(
              forgetStudentConversation(indexRef.current, course.course_id),
            )
            continue
          } else {
            setConversation(view.conversation)
            saveIndex(rememberStudentConversation(indexRef.current, course.course_id, view.conversation.id))
            setMessages(view.messages)
            const interrupted = readPendingStudentRequest(accountId, view.conversation.id)
            if (interrupted) {
              const sent = view.messages.find(message => message.role === "student" && message.client_request_id === interrupted.requestId)
              const completed = sent && view.messages.some(message => message.role === "tutor" && message.response_to_message_id === sent.id)
              if (completed) {
                savePendingStudentRequest(accountId, view.conversation.id, null)
              } else {
                pendingRequestRef.current = interrupted
                setDraft(interrupted.content)
                setError({ scope: "message", code: "interrupted_send", message: "The previous send was interrupted. It may still finish. Try again recovers that same send without starting a duplicate." })
              }
            }
            setPendingClarification(view.pending_clarification ?? null)
            setIsLoadingConversation(false)
            void readEvidence(view.conversation.id, operation)
            void readCitations(view.messages, operation)
            return
          }
        } catch (caught) {
          if (operation !== operationRef.current) return
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
        setConversationHistory((current) => [created, ...current.filter((item) => item.id !== created.id && isConversationForCurrentRelease(item, course))])
        setLearnerEvidence(null)
        setPendingClarification(null)
        setIsLoadingConversation(false)
      } catch (caught) {
        if (operation !== operationRef.current) return
        setError(toWorkspaceError(caught, "workspace"))
        setIsLoadingConversation(false)
      }
    },
    [accountId, saveIndex, readEvidence, readCitations],
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
        outreachCourseRef.current = null
        ++outreachScopeRef.current
        ++outreachOperationRef.current
        setLearnerEvidence(null)
        setPendingClarification(null)
        pendingRequestRef.current = null
        outreachReplyRef.current = null
        setOutreachReply(null)
        setDraft("")
        setIsLoadingConversation(false)
        setActiveCourse(null)
        setConversation(null)
        setConversationHistory([])
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
    const started = startedRef, operations = operationRef, evidenceReads = evidenceReadRef, citationReads = citationReadRef
    return () => {
      started.current = false
      ++operations.current
      ++evidenceReads.current
      ++citationReads.current
    }
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
      ++outreachOperationRef.current
      setIsLoadingOutreach(false)
      setOutreachMessages([])
      setOutreachPreferences([])
      setAutonomousGoals([])
      return
    }
    void loadOutreach(courseId)
    const interval = window.setInterval(() => {
      void loadOutreach(courseId, true)
    }, 30_000)
    const operations = outreachOperationRef
    return () => {
      window.clearInterval(interval)
      ++operations.current
    }
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

  const selectConversation = useCallback(async (conversationId: string) => {
    if (!activeCourse || isSubmitting || isLoadingConversation) return
    if (!conversationHistory.some((item) => item.id === conversationId && isConversationForCurrentRelease(item, activeCourse))) return
    await loadConversation(activeCourse, conversationId)
  }, [activeCourse, conversationHistory, isSubmitting, isLoadingConversation, loadConversation])

  const startNewConversation = useCallback(async () => {
    if (!activeCourse || isSubmitting) return
    saveIndex(forgetStudentConversation(indexRef.current, activeCourse.course_id))
    await loadConversation(activeCourse, undefined, true)
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

  const sendContent = useCallback(async (rawContent: string) => {
    const content = rawContent.trim()
    if (!content || !conversation || isSubmitting || submitLockRef.current) return

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
    savePendingStudentRequest(accountId, conversation.id, request)
    const operation = operationRef.current
    submitLockRef.current = true
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
      ++citationSelectionRef.current
      setSelectedCitation(turn.citations[0] ?? null)
      setPendingClarification(turn.pending_clarification ?? null)
      setDraft("")
      outreachReplyRef.current = null
      setOutreachReply(null)
      pendingRequestRef.current = null
      savePendingStudentRequest(accountId, conversation.id, null)
      submitLockRef.current = false
      setIsSubmitting(false)
      void readEvidence(conversation.id, operation)
    } catch (caught) {
      if (operation !== operationRef.current) return
      setError(toWorkspaceError(caught, "message"))
    } finally {
      if (operation === operationRef.current) {
        submitLockRef.current = false
        setIsSubmitting(false)
      }
    }
  }, [accountId, conversation, isSubmitting, readEvidence])

  const sendMessage = useCallback(
    async () => sendContent(draft),
    [draft, sendContent],
  )

  const chooseClarification = useCallback(
    async (optionId: string) => {
      setDraft(optionId)
      await sendContent(optionId)
    },
    [sendContent],
  )

  const selectCitation = useCallback(
    (messageId: string, citationId: string) => {
      const citation = citationsByMessage[messageId]?.find(
        (entry) => entry.id === citationId,
      )
      if (citation) {
        ++citationSelectionRef.current
        setSelectedCitation(citation)
      }
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
      const scope = outreachScopeRef.current
      setIsUpdatingOutreach(true)
      setOutreachError(null)
      try {
        const preference = await updateStudentInAppOutreachPreference(
          activeCourse.course_id,
          enabled,
          accountId,
        )
        if (scope !== outreachScopeRef.current) return
        ++outreachOperationRef.current
        setIsLoadingOutreach(false)
        setOutreachPreferences((current) => [
          ...current.filter((item) => item.channel !== "in-app"),
          preference,
        ])
      } catch (caught) {
        if (scope !== outreachScopeRef.current) return
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      } finally {
        if (scope === outreachScopeRef.current) setIsUpdatingOutreach(false)
      }
    },
    [accountId, activeCourse, isUpdatingOutreach],
  )

  const snoozeOutreach = useCallback(
    async (days: number | null) => {
      if (!activeCourse || isUpdatingOutreach || (days !== null && days < 1)) return
      const scope = outreachScopeRef.current
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
        if (scope !== outreachScopeRef.current) return
        ++outreachOperationRef.current
        setIsLoadingOutreach(false)
        setOutreachPreferences((current) => [
          ...current.filter((item) => item.channel !== "in-app"),
          preference,
        ])
      } catch (caught) {
        if (scope !== outreachScopeRef.current) return
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      } finally {
        if (scope === outreachScopeRef.current) setIsUpdatingOutreach(false)
      }
    },
    [accountId, activeCourse, isUpdatingOutreach],
  )

  const markOutreachRead = useCallback(
    async (messageId: string) => {
      const scope = outreachScopeRef.current
      try {
        const updated = await markStudentOutreachRead(messageId, accountId)
        if (scope !== outreachScopeRef.current) return
        ++outreachOperationRef.current
        setIsLoadingOutreach(false)
        setOutreachMessages((current) =>
          current.map((item) =>
            item.message.id === messageId ? updated : item,
          ),
        )
      } catch (caught) {
        if (scope !== outreachScopeRef.current) return
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      }
    },
    [accountId],
  )

  const dismissOutreach = useCallback(
    async (messageId: string) => {
      const scope = outreachScopeRef.current
      try {
        await dismissStudentOutreach(messageId, accountId)
        if (scope !== outreachScopeRef.current) return
        ++outreachOperationRef.current
        setIsLoadingOutreach(false)
        setOutreachMessages((current) =>
          current.filter((item) => item.message.id !== messageId),
        )
      } catch (caught) {
        if (scope !== outreachScopeRef.current) return
        setOutreachError(toWorkspaceError(caught, "workspace").message)
      }
    },
    [accountId],
  )

  const replyToOutreach = useCallback((messageId: string) => {
    if (isSubmitting || !conversation || isLoadingConversation) return
    const selected = outreachMessages.find((item) => item.message.id === messageId)
    if (!selected) return
    outreachReplyRef.current = messageId
    setOutreachReply(selected)
    pendingRequestRef.current = null
    savePendingStudentRequest(accountId, conversation.id, null)
  }, [accountId, conversation, isLoadingConversation, isSubmitting, outreachMessages])

  const cancelOutreachReply = useCallback(() => {
    if (isSubmitting) return
    outreachReplyRef.current = null
    setOutreachReply(null)
    pendingRequestRef.current = null
    if (conversation) savePendingStudentRequest(accountId, conversation.id, null)
  }, [accountId, conversation, isSubmitting])

  useEffect(() => {
    const replyId = pendingRequestRef.current?.respondingToOutreachMessageId
    const reply = outreachMessages.find(item => item.message.id === replyId)
    if (reply && !outreachReplyRef.current) {
      outreachReplyRef.current = reply.message.id
      setOutreachReply(reply)
    }
  }, [conversation, outreachMessages])

  return {
    accountId,
    courses,
    activeCourse,
    conversation,
    conversationHistory,
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
      error?.code === "release_unavailable" ||
      error?.code === "profile_mismatch" ||
      error?.code === "turn_authority_changed",
    setDraft,
    reload,
    selectCourse,
    selectConversation,
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

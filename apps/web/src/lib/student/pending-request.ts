// Tab-local recovery only; never resubmit a tutoring request automatically.
export type PendingStudentRequest = {
  content: string
  requestId: string
  respondingToOutreachMessageId?: string
}

function key(accountId: string, conversationId: string) {
  return `course-digital-twin.pending-send.v1.${encodeURIComponent(accountId)}.${encodeURIComponent(conversationId)}`
}

export function readPendingStudentRequest(accountId: string, conversationId: string): PendingStudentRequest | null {
  try {
    const value = JSON.parse(window.sessionStorage.getItem(key(accountId, conversationId)) ?? 'null')
    if (!value || typeof value.content !== 'string' || !value.content.trim() || value.content.length > 8000
      || typeof value.requestId !== 'string' || !value.requestId || value.requestId.length > 128
      || (value.respondingToOutreachMessageId !== undefined && typeof value.respondingToOutreachMessageId !== 'string')) return null
    return { content: value.content, requestId: value.requestId,
      ...(value.respondingToOutreachMessageId ? { respondingToOutreachMessageId: value.respondingToOutreachMessageId } : {}) }
  } catch {
    return null
  }
}

export function savePendingStudentRequest(accountId: string, conversationId: string, request: PendingStudentRequest | null) {
  try {
    if (request) window.sessionStorage.setItem(key(accountId, conversationId), JSON.stringify(request))
    else window.sessionStorage.removeItem(key(accountId, conversationId))
  } catch {
    // Storage may be disabled; ordinary sending and server idempotency still work.
  }
}

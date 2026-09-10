import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createHookHarness, deferred } from './testing/hook-harness'
import type { StudentCourse, StudentOutreachPreference } from '@/lib/api/types'
const h = vi.hoisted(() => ({ current: null as ReturnType<typeof createHookHarness> | null }))
vi.mock('react', () => ({
  useState: (...args: [unknown]) => h.current!.react.useState(...args),
  useRef: (...args: [unknown]) => h.current!.react.useRef(...args),
  useCallback: (...args: [unknown, unknown[]]) => h.current!.react.useCallback(...args),
  useEffect: (...args: [() => void | (() => void), unknown[]]) => h.current!.react.useEffect(...args),
}))
vi.mock('@/lib/api', () => ({
  STUDENT_ACCOUNT_ID: 'synthetic', StudentApiError: class extends Error {},
  listStudentCourses: vi.fn(), listStudentConversations: vi.fn(), createStudentConversation: vi.fn(),
  listStudentOutreach: vi.fn(), listStudentOutreachPreferences: vi.fn(), listStudentAutonomousGoals: vi.fn(),
  updateStudentInAppOutreachPreference: vi.fn(), getStudentConversation: vi.fn(), getStudentLearnerEvidence: vi.fn(),
  dismissStudentOutreach: vi.fn(), markStudentOutreachRead: vi.fn(), submitStudentMessage: vi.fn(), listStudentMessageCitations: vi.fn(),
}))
import * as api from '@/lib/api'
import { useStudentWorkspace } from './use-student-workspace'
const a = { course_id: 'a', release_id: 'ra' } as StudentCourse
const b = { course_id: 'b', release_id: 'rb' } as StudentCourse
const pref = (course: string, enabled: boolean) => ({ course_id: course, channel: 'in-app', enabled }) as StudentOutreachPreference
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve() }
let render: () => ReturnType<typeof useStudentWorkspace>
beforeEach(() => {
  vi.resetAllMocks(); h.current = createHookHarness()
  vi.stubGlobal('window', { localStorage: { getItem: () => null, setItem: vi.fn() }, setInterval: vi.fn(), clearInterval: vi.fn() })
  vi.mocked(api.listStudentCourses).mockResolvedValue([a, b])
  vi.mocked(api.listStudentConversations).mockResolvedValue([])
  vi.mocked(api.createStudentConversation).mockImplementation(async id => ({ id: `conv-${id}`, course_id: id }) as never)
  vi.mocked(api.listStudentOutreach).mockResolvedValue([])
  vi.mocked(api.listStudentAutonomousGoals).mockResolvedValue([])
  vi.mocked(api.listStudentOutreachPreferences).mockImplementation(async id => [pref(id, false)])
  render = () => h.current!.render(() => useStudentWorkspace('synthetic'))
})
async function ready() { render(); await tick(); render(); await tick(); return render() }
describe('server conversation discovery', () => {
  it('resumes current-release history without browser storage and keeps New chat explicit', async () => {
    const saved = { id: 'saved-a', course_id: 'a', release_id: 'ra' }
    vi.mocked(api.listStudentConversations).mockResolvedValue([saved] as never)
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: [] } as never)
    vi.mocked(api.getStudentLearnerEvidence).mockResolvedValue(null as never)
    let state = await ready()
    expect(state.conversation?.id).toBe('saved-a')
    expect(api.createStudentConversation).not.toHaveBeenCalled()
    await state.startNewConversation(); state = render()
    expect(api.createStudentConversation).toHaveBeenCalledWith('a', 'synthetic')
    expect(state.conversation?.id).toBe('conv-a')
    expect(api.listStudentConversations).toHaveBeenCalledTimes(1)
  })
  it('shows discovery failure without creating a duplicate conversation', async () => {
    vi.mocked(api.listStudentConversations).mockRejectedValue(new Error('History unavailable'))
    const state = await ready()
    expect(state.error?.message).toContain('History unavailable')
    expect(state.isLoadingConversation).toBe(false)
    expect(api.createStudentConversation).not.toHaveBeenCalled()
  })
  it('ignores a delayed discovery after the selected course changes', async () => {
    const pending = deferred<never[]>()
    vi.mocked(api.listStudentConversations).mockReturnValueOnce(pending.promise)
    render(); await tick(); let state = render()
    await state.selectCourse('b'); state = render()
    pending.resolve([{ id: 'old-a', course_id: 'a', release_id: 'ra' }] as never)
    await tick(); state = render()
    expect(state.activeCourse?.course_id).toBe('b')
    expect(state.conversation?.id).toBe('conv-b')
    expect(api.getStudentConversation).not.toHaveBeenCalled()
  })
})
describe('student course request isolation', () => {
  it('does not apply a delayed course A opt-in to course B', async () => {
    let state = await ready()
    const pending = deferred<StudentOutreachPreference>()
    vi.mocked(api.updateStudentInAppOutreachPreference).mockReturnValue(pending.promise)
    const update = state.setInAppOutreachEnabled(true)
    state = render(); await state.selectCourse('b'); render(); await tick(); state = render()
    expect(state.activeCourse?.course_id).toBe('b')
    pending.resolve(pref('a', true)); await update
    expect(render().inAppOutreachEnabled).toBe(false)
  })
  it('clears old outreach while the new course request is pending', async () => {
    vi.mocked(api.listStudentOutreachPreferences).mockResolvedValue([pref('a', true)])
    let state = await ready(); expect(state.inAppOutreachEnabled).toBe(true)
    const pending = deferred<StudentOutreachPreference[]>()
    vi.mocked(api.listStudentOutreachPreferences).mockReturnValue(pending.promise)
    await state.selectCourse('b'); render(); state = render()
    expect(state.inAppOutreachEnabled).toBe(false)
  })
  it('does not apply delayed snooze failure to another course', async () => {
    let state = await ready()
    const pending = deferred<StudentOutreachPreference>()
    vi.mocked(api.updateStudentInAppOutreachPreference).mockReturnValue(pending.promise)
    const update = state.snoozeOutreach(2)
    state = render(); await state.selectCourse('b'); render(); await tick()
    pending.reject(new Error('old course request failed')); await update
    state = render(); expect(state.outreachError).toBeNull(); expect(state.isUpdatingOutreach).toBe(false)
  })
  it('invalidates an earlier preference poll when a newer opt-in saves', async () => {
    let state = await ready()
    const pending = deferred<StudentOutreachPreference[]>()
    vi.mocked(api.listStudentOutreachPreferences).mockReturnValue(pending.promise)
    const refresh = state.refreshOutreach()
    vi.mocked(api.updateStudentInAppOutreachPreference).mockResolvedValue(pref('a', true))
    await state.setInAppOutreachEnabled(true)
    pending.resolve([pref('a', false)]); await refresh
    expect(render().inAppOutreachEnabled).toBe(true)
  })
  it('does not restore outreach when all course access disappears', async () => {
    let state = await ready()
    const pending = deferred<StudentOutreachPreference[]>()
    vi.mocked(api.listStudentOutreachPreferences).mockReturnValue(pending.promise)
    const refresh = state.refreshOutreach()
    vi.mocked(api.listStudentCourses).mockResolvedValue([])
    await state.reload(); render()
    pending.resolve([pref('a', true)]); await refresh
    state = render(); expect(state.activeCourse).toBeNull(); expect(state.inAppOutreachEnabled).toBe(false)
  })

})

describe('check-in reply context and request lineage', () => {
  const checkIn = (id: string) => ({ message: { id, course_id: 'a', content: `Original question ${id}`, status: 'delivered' }, citations: [] }) as never
  const turn = { student_message: { id: 'student-reply' }, tutor_message: { id: 'tutor-reply' }, citations: [] } as never

  async function replying() {
    vi.mocked(api.listStudentOutreach).mockResolvedValue([checkIn('first'), checkIn('second')])
    let state = await ready()
    state.setDraft('My existing answer')
    state = render()
    state.replyToOutreach('first')
    return render()
  }

  it('keeps the original question and existing draft visible, then clears context only after success', async () => {
    let state = await replying()
    expect(state.outreachReply?.message.content).toBe('Original question first')
    expect(state.draft).toBe('My existing answer')
    vi.mocked(api.submitStudentMessage).mockResolvedValue(turn)
    await state.sendMessage()
    expect(api.submitStudentMessage).toHaveBeenCalledWith('conv-a', 'My existing answer', expect.any(String), 'synthetic', 'first')
    state = render()
    expect(state.outreachReply).toBeNull()
    expect(state.draft).toBe('')
  })

  it('keeps reply context and the same request ID after a failed send', async () => {
    let state = await replying()
    vi.mocked(api.submitStudentMessage).mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce(turn)
    await state.sendMessage()
    state = render()
    expect(state.outreachReply?.message.id).toBe('first')
    expect(state.draft).toBe('My existing answer')
    await state.sendMessage()
    const calls = vi.mocked(api.submitStudentMessage).mock.calls
    expect(calls[1]).toEqual(calls[0])
    expect(render().outreachReply).toBeNull()
  })

  it('cancels the reply association without deleting the draft or reusing a failed reply request', async () => {
    let state = await replying()
    vi.mocked(api.submitStudentMessage).mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce(turn)
    await state.sendMessage()
    state = render()
    state.cancelOutreachReply()
    state = render()
    expect(state.outreachReply).toBeNull()
    expect(state.draft).toBe('My existing answer')
    await state.sendMessage()
    const calls = vi.mocked(api.submitStudentMessage).mock.calls
    expect(calls[1][4]).toBeUndefined()
    expect(calls[1][2]).not.toBe(calls[0][2])
  })

  it('uses the newly selected check-in after switching replies with identical text', async () => {
    let state = await replying()
    vi.mocked(api.submitStudentMessage).mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce(turn)
    await state.sendMessage()
    state = render()
    state.replyToOutreach('second')
    state = render()
    expect(state.outreachReply?.message.content).toBe('Original question second')
    await state.sendMessage()
    const calls = vi.mocked(api.submitStudentMessage).mock.calls
    expect(calls[1][4]).toBe('second')
    expect(calls[1][2]).not.toBe(calls[0][2])
  })

  it('does not change the displayed reply while its send is in flight', async () => {
    let state = await replying()
    const pending = deferred<typeof turn>()
    vi.mocked(api.submitStudentMessage).mockReturnValue(pending.promise)
    const sending = state.sendMessage()
    state = render()
    state.replyToOutreach('second')
    state.cancelOutreachReply()
    expect(render().outreachReply?.message.id).toBe('first')
    pending.resolve(turn)
    await sending
    expect(render().outreachReply).toBeNull()
  })

  it('clears reply context when changing course and rejects unknown check-ins', async () => {
    let state = await replying()
    await state.selectCourse('b')
    state = render()
    expect(state.outreachReply).toBeNull()
    state.replyToOutreach('not-in-this-inbox')
    expect(render().outreachReply).toBeNull()
  })
})


describe('independent chat metadata recovery', () => {
  const saved = { id: 'saved-a', course_id: 'a', release_id: 'ra' }
  const message = (id: string, role = 'tutor') => ({ id, role, content: id })
  const turn = (id: string) => ({ student_message: message('s' + id, 'student'), tutor_message: message('t' + id), citations: [{ id: 'c' + id }] })
  function history() {
    vi.mocked(api.listStudentConversations).mockResolvedValue([saved] as never)
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: [message('old1'), message('old2')] } as never)
    vi.mocked(api.listStudentMessageCitations).mockResolvedValue([])
    vi.mocked(api.getStudentLearnerEvidence).mockResolvedValue(null as never)
  }
  it('releases the composer before evidence settles and rejects rapid duplicate clicks', async () => {
    let state = await ready()
    const evidence = deferred<never>()
    vi.mocked(api.submitStudentMessage).mockResolvedValue(turn('1') as never)
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValue(evidence.promise)
    state.setDraft('Question'); state = render()
    await Promise.all([state.sendMessage(), state.sendMessage()]); state = render()
    expect(state.messages.map(m => m.id)).toEqual(['s1', 't1'])
    expect(state.isSubmitting).toBe(false); expect(state.draft).toBe('')
    expect(state.evidenceStatus).toBe('loading')
    expect(api.submitStudentMessage).toHaveBeenCalledTimes(1)
    evidence.reject(new Error('offline')); await tick(); state = render()
    expect(state.evidenceStatus).toBe('error'); expect(state.error).toBeNull()
  })
  it('shows saved history while both metadata reads stall', async () => {
    history(); const evidence = deferred<never>(), citations = deferred<never>()
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValue(evidence.promise)
    vi.mocked(api.listStudentMessageCitations).mockReturnValue(citations.promise)
    const state = await ready()
    expect(state.messages).toHaveLength(2); expect(state.isLoadingConversation).toBe(false)
    expect(state.evidenceStatus).toBe('loading'); expect(state.citationsStatus).toBe('loading')
    expect(api.createStudentConversation).not.toHaveBeenCalled()
    evidence.resolve(null as never); citations.resolve([] as never); await tick()
  })
  it('leaves connections available while a long history loads citations', async () => {
    history()
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: Array.from({ length: 8 }, (_, i) => message(`old${i}`)) } as never)
    const reads = Array.from({ length: 8 }, () => deferred<never>())
    vi.mocked(api.listStudentMessageCitations).mockImplementation(id => reads[Number(id.slice(3))].promise)
    let state = await ready()
    expect(state.messages).toHaveLength(8)
    expect(state.isLoadingConversation).toBe(false)
    expect(api.listStudentMessageCitations).toHaveBeenCalledTimes(2)
    reads[0].resolve([{ id: 'first' }] as never); await tick()
    expect(api.listStudentMessageCitations).toHaveBeenCalledTimes(3)
    for (const read of reads.slice(1)) read.resolve([] as never)
    for (let i = 0; i < 4; i++) await tick()
    state = render()
    expect(state.citationsStatus).toBe('ready')
    expect(api.listStudentMessageCitations).toHaveBeenCalledTimes(8)
    expect(api.submitStudentMessage).not.toHaveBeenCalled()
  })
  it('does not start queued citation reads after leaving their conversation', async () => {
    history()
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: Array.from({ length: 8 }, (_, i) => message(`old${i}`)) } as never)
    const pending = deferred<never>()
    vi.mocked(api.listStudentMessageCitations).mockReturnValue(pending.promise)
    const state = await ready()
    await state.startNewConversation()
    pending.resolve([] as never); await tick()
    expect(api.listStudentMessageCitations).toHaveBeenCalledTimes(2)
    expect(render().citationsByMessage).toEqual({})
  })
  it('keeps successful citations and retries failed metadata without tutoring or creation', async () => {
    history()
    vi.mocked(api.listStudentMessageCitations).mockImplementation(async id => { if (id === 'old2') throw new Error('offline'); return [{ id: 'c-old1' }] as never })
    vi.mocked(api.getStudentLearnerEvidence).mockRejectedValue(new Error('unavailable'))
    let state = await ready()
    expect(state.citationsByMessage.old1).toEqual([{ id: 'c-old1' }]); expect(state.citationsStatus).toBe('error')
    expect(state.messages).toHaveLength(2); expect(state.error).toBeNull()
    vi.mocked(api.listStudentMessageCitations).mockResolvedValue([{ id: 'recovered' }] as never)
    vi.mocked(api.getStudentLearnerEvidence).mockResolvedValue({ belief_state: { revision: 2 } } as never)
    await Promise.all([state.retryCitations(), state.retryEvidence()]); state = render()
    expect(state.citationsStatus).toBe('ready'); expect(state.evidenceStatus).toBe('ready')
    expect(state.citationsByMessage.old1).toEqual([{ id: 'c-old1' }]); expect(state.citationsByMessage.old2).toEqual([{ id: 'recovered' }])
    expect(api.submitStudentMessage).not.toHaveBeenCalled(); expect(api.createStudentConversation).not.toHaveBeenCalled()
  })
  it('preserves failed-send request IDs on manual retry', async () => {
    let state = await ready()
    vi.mocked(api.submitStudentMessage).mockRejectedValueOnce(new Error('lost response')).mockResolvedValueOnce(turn('1') as never)
    vi.mocked(api.getStudentLearnerEvidence).mockResolvedValue(null as never)
    state.setDraft('Question'); state = render(); await state.sendMessage(); state = render()
    expect(state.draft).toBe('Question'); await state.sendMessage()
    const calls = vi.mocked(api.submitStudentMessage).mock.calls
    expect(calls[0]).toEqual(calls[1]); expect(render().messages).toHaveLength(2)
  })
  it('ignores older evidence after a newer turn and retains current evidence while updating', async () => {
    history(); vi.mocked(api.getStudentLearnerEvidence).mockResolvedValue({ belief_state: { revision: 1 } } as never)
    let state = await ready(); const old = deferred<never>()
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValueOnce(old.promise).mockResolvedValueOnce({ belief_state: { revision: 3 } } as never)
    vi.mocked(api.submitStudentMessage).mockResolvedValueOnce(turn('1') as never).mockResolvedValueOnce(turn('2') as never)
    state.setDraft('One'); state = render(); await state.sendMessage(); state = render()
    expect(state.learnerEvidence?.belief_state?.revision).toBe(1)
    state.setDraft('Two'); state = render(); await state.sendMessage(); await tick()
    old.resolve({ belief_state: { revision: 2 } } as never); await tick()
    expect(render().learnerEvidence?.belief_state?.revision).toBe(3)
    expect(api.submitStudentMessage).toHaveBeenCalledTimes(2)
  })
  it('ignores metadata from the previous course', async () => {
    history(); const evidence = deferred<never>(), citations = deferred<never>()
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValue(evidence.promise)
    vi.mocked(api.listStudentMessageCitations).mockReturnValue(citations.promise)
    let state = await ready(); await state.selectCourse('b'); state = render()
    evidence.resolve({ belief_state: { revision: 99 } } as never); citations.resolve([{ id: 'old' }] as never); await tick()
    state = render(); expect(state.conversation?.id).toBe('conv-b'); expect(state.learnerEvidence).toBeNull()
    expect(state.citationsByMessage).toEqual({}); expect(state.evidenceStatus).toBe('idle')
  })
  it('does not replace the latest turn citation when saved citations arrive late', async () => {
    history(); const citations = deferred<never>()
    vi.mocked(api.listStudentMessageCitations).mockReturnValue(citations.promise)
    let state = await ready(); vi.mocked(api.submitStudentMessage).mockResolvedValue(turn('new') as never)
    state.setDraft('New question'); state = render(); await state.sendMessage()
    citations.resolve([{ id: 'old-source' }] as never); await tick(); state = render()
    expect(state.selectedCitation?.id).toBe('cnew'); expect(state.citationsByMessage.tnew).toEqual([{ id: 'cnew' }])
  })
  it('ignores an older manual retry and invalidates pending reads on unmount', async () => {
    history(); let state = await ready(); const old = deferred<never>()
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValueOnce(old.promise).mockResolvedValueOnce({ belief_state: { revision: 5 } } as never)
    const first = state.retryEvidence(); await state.retryEvidence()
    old.resolve({ belief_state: { revision: 4 } } as never); await first
    expect(render().learnerEvidence?.belief_state?.revision).toBe(5)
    const detached = deferred<never>(); vi.mocked(api.getStudentLearnerEvidence).mockReturnValue(detached.promise)
    state = render(); const last = state.retryEvidence(); h.current!.unmount()
    detached.resolve({ belief_state: { revision: 6 } } as never); await last
    expect(render().learnerEvidence?.belief_state?.revision).toBe(5)
  })
  it('ignores evidence from the previous conversation in the same course', async () => {
    history(); const evidence = deferred<never>()
    vi.mocked(api.getStudentLearnerEvidence).mockReturnValue(evidence.promise)
    let state = await ready(); await state.startNewConversation()
    evidence.resolve({ belief_state: { revision: 99 } } as never); await tick(); state = render()
    expect(state.conversation?.id).toBe('conv-a'); expect(state.learnerEvidence).toBeNull()
  })

})

describe('interrupted send recovery after page reload', () => {
  function sessionStore() {
    const data = new Map<string, string>()
    Object.assign(window, { sessionStorage: {
      getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => { data.set(key, value) },
      removeItem: (key: string) => { data.delete(key) },
    } })
    return data
  }
  async function pendingSend() {
    const store = sessionStore()
    const saved = { id: 'saved-a', course_id: 'a', release_id: 'ra' }
    vi.mocked(api.listStudentConversations).mockResolvedValue([saved] as never)
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: [] } as never)
    let state = await ready()
    state.setDraft('My interrupted question'); state = render()
    const pending = deferred<never>()
    vi.mocked(api.submitStudentMessage).mockReturnValueOnce(pending.promise)
    const send = state.sendMessage()
    h.current!.unmount(); h.current = createHookHarness()
    return { store, pending, send, saved }
  }
  it('restores an interrupted draft and retries only manually with its original request ID', async () => {
    const { pending, send } = await pendingSend()
    const state = await ready()
    expect(state.draft).toBe('My interrupted question')
    expect(state.error?.message).toContain('interrupted')
    expect(api.submitStudentMessage).toHaveBeenCalledTimes(1)
    vi.mocked(api.submitStudentMessage).mockResolvedValue({ student_message: { id: 's' }, tutor_message: { id: 't' }, citations: [] } as never)
    await state.sendMessage()
    expect(vi.mocked(api.submitStudentMessage).mock.calls[1]).toEqual(vi.mocked(api.submitStudentMessage).mock.calls[0])
    pending.reject(new Error('old page disconnected')); await send
  })
  it('recognizes a committed response on reload and does not restore or resend its draft', async () => {
    const { store, pending, send, saved } = await pendingSend()
    expect(store.size).toBe(1)
    const id = vi.mocked(api.submitStudentMessage).mock.calls[0][2]
    vi.mocked(api.getStudentConversation).mockResolvedValue({ conversation: saved, messages: [
      { id: 's', role: 'student', client_request_id: id }, { id: 't', role: 'tutor', response_to_message_id: 's' },
    ] } as never)
    const state = await ready()
    expect(state.draft).toBe(''); expect(state.error).toBeNull()
    expect(store.size).toBe(0); expect(api.submitStudentMessage).toHaveBeenCalledTimes(1)
    pending.reject(new Error('old page disconnected')); await send
  })
  it('does not restore another account pending draft', async () => {
    const { store, pending, send } = await pendingSend()
    expect(store.size).toBe(1)
    render = () => h.current!.render(() => useStudentWorkspace('other-account'))
    const state = await ready()
    expect(state.draft).toBe(''); expect(state.error).toBeNull()
    pending.reject(new Error('old page disconnected')); await send
  })
})

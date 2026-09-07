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
  listStudentCourses: vi.fn(), createStudentConversation: vi.fn(),
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
  vi.mocked(api.createStudentConversation).mockImplementation(async id => ({ id: `conv-${id}`, course_id: id }) as never)
  vi.mocked(api.listStudentOutreach).mockResolvedValue([])
  vi.mocked(api.listStudentAutonomousGoals).mockResolvedValue([])
  vi.mocked(api.listStudentOutreachPreferences).mockImplementation(async id => [pref(id, false)])
  render = () => h.current!.render(() => useStudentWorkspace('synthetic'))
})
async function ready() { render(); await tick(); render(); await tick(); return render() }
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

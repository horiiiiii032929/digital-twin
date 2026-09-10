import { beforeEach, expect, it, vi } from 'vitest'
import { createHookHarness, deferred } from './testing/hook-harness'
import type { IdentityProfile } from '@/lib/api/types'
const h = vi.hoisted(() => ({ current: null as ReturnType<typeof createHookHarness> | null }))
vi.mock('react', () => ({
  useState: (...args: [unknown]) => h.current!.react.useState(...args),
  useRef: (...args: [unknown]) => h.current!.react.useRef(...args),
  useCallback: (...args: [unknown, unknown[]]) => h.current!.react.useCallback(...args),
  useEffect: (...args: [() => void | (() => void), unknown[]]) => h.current!.react.useEffect(...args),
}))
vi.mock('@/lib/api', () => ({ ApiError: class extends Error {}, login: vi.fn(), logout: vi.fn(), changePassword: vi.fn(), getCurrentSession: vi.fn() }))
import * as api from '@/lib/api'
import { useAuthSession } from './use-auth-session'
beforeEach(() => { h.current?.unmount(); vi.resetAllMocks(); h.current = createHookHarness(); vi.mocked(api.getCurrentSession).mockResolvedValue(null as never) })
it('admits only one credential mutation before React can disable the form', async () => {
  const pending = deferred<IdentityProfile>()
  vi.mocked(api.login).mockReturnValue(pending.promise)
  const auth = h.current!.render(useAuthSession)
  const first = auth.signIn('one@example.test', 'synthetic')
  await auth.signIn('two@example.test', 'synthetic')
  await auth.signOut()
  expect(api.login).toHaveBeenCalledTimes(1); expect(api.logout).not.toHaveBeenCalled()
  pending.resolve({ account_id: 'one', role: 'student' } as IdentityProfile); await first
  expect(h.current!.render(useAuthSession).profile?.account_id).toBe('one')
  await auth.signOut(); expect(api.logout).toHaveBeenCalledTimes(1)
})
it('releases the admission guard after a failed sign-in', async () => {
  vi.mocked(api.login).mockRejectedValueOnce(new Error('failed')).mockResolvedValueOnce({ account_id: 'one' } as IdentityProfile)
  const auth = h.current!.render(useAuthSession)
  await auth.signIn('one@example.test', 'synthetic'); await auth.signIn('one@example.test', 'synthetic')
  expect(api.login).toHaveBeenCalledTimes(2)
})

it('returns to sign-in after a protected request reports an expired session', async () => {
  const { listStudentCourses } = await import('@/lib/api/student')
  vi.mocked(api.getCurrentSession).mockResolvedValue({ account_id: 'one', role: 'student' } as IdentityProfile)
  h.current!.render(useAuthSession); await Promise.resolve(); await Promise.resolve()
  expect(h.current!.render(useAuthSession).profile?.account_id).toBe('one')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { message: 'Session expired' } }), { status: 401 })))
  await expect(listStudentCourses('one')).rejects.toThrow('Session expired')
  const state = h.current!.render(useAuthSession)
  expect(state.profile).toBeNull()
  expect(state.error).toContain('Sign in again')
  vi.unstubAllGlobals()
})

it('ignores a late expired response from before a new sign-in', async () => {
  const { listStudentCourses } = await import('@/lib/api/student')
  const pending = deferred<Response>()
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(pending.promise))
  let state = h.current!.render(useAuthSession)
  await Promise.resolve(); await Promise.resolve()
  const old = listStudentCourses('old')
  vi.mocked(api.login).mockResolvedValue({ account_id: 'new', role: 'student' } as IdentityProfile)
  await state.signIn('new@example.test', 'synthetic')
  pending.resolve(new Response(JSON.stringify({ detail: 'Expired old session' }), { status: 401 }))
  await expect(old).rejects.toThrow('Expired old session')
  state = h.current!.render(useAuthSession)
  expect(state.profile?.account_id).toBe('new')
  vi.unstubAllGlobals()
})

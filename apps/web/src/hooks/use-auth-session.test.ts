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
beforeEach(() => { vi.resetAllMocks(); h.current = createHookHarness(); vi.mocked(api.getCurrentSession).mockResolvedValue(null as never) })
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

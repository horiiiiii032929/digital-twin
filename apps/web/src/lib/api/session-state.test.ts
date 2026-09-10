import { afterEach, expect, it, vi } from 'vitest'
import { request } from './client'
import { advanceSessionRevision, onSessionExpired } from './session-state'
afterEach(() => { vi.unstubAllGlobals(); advanceSessionRevision() })
it.each([['/api/professor/courses',401,1],['/api/admin/accounts',401,1],['/api/auth/login',401,0],['/api/auth/password',401,0],['/api/professor/courses',403,0]] as const)(
  'preserves HTTP failure while routing %s status %i to auth only when appropriate', async (path,status,count) => {
    const expired = vi.fn(); const unsubscribe = onSessionExpired(expired)
    try {
      vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Request denied'}),{status})))
      await expect(request(path)).rejects.toMatchObject({status,message:'Request denied'})
      expect(expired).toHaveBeenCalledTimes(count)
    } finally { unsubscribe() }
  })

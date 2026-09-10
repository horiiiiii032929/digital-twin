import { afterEach, expect, it, vi } from 'vitest'
import { readPendingStudentRequest, savePendingStudentRequest } from './pending-request'
afterEach(() => vi.unstubAllGlobals())
it('isolates requests by account and conversation and removes confirmed markers', () => {
  const data = new Map<string, string>()
  vi.stubGlobal('window', { sessionStorage: {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => data.set(key, value),
    removeItem: (key: string) => data.delete(key),
  } })
  const request = { content: 'SQL café', requestId: 'request-1', respondingToOutreachMessageId: 'check-in-1' }
  savePendingStudentRequest('student/a', 'conversation/a', request)
  expect(readPendingStudentRequest('student/a', 'conversation/a')).toEqual(request)
  expect(readPendingStudentRequest('student/b', 'conversation/a')).toBeNull()
  expect(readPendingStudentRequest('student/a', 'conversation/b')).toBeNull()
  savePendingStudentRequest('student/a', 'conversation/a', null)
  expect(data.size).toBe(0)
})
it('does not break ordinary sending when browser storage is blocked', () => {
  vi.stubGlobal('window', { get sessionStorage() { throw new Error('Storage blocked') } })
  expect(() => savePendingStudentRequest('a', 'c', { content: 'question', requestId: 'r' })).not.toThrow()
  expect(readPendingStudentRequest('a', 'c')).toBeNull()
})
it.each(['not json', '{}', '{"content":"","requestId":"r"}', '{"content":"q","requestId":3}'])(
  'ignores malformed tab storage: %s', raw => {
    vi.stubGlobal('window', { sessionStorage: { getItem: () => raw } })
    expect(readPendingStudentRequest('a', 'c')).toBeNull()
  })

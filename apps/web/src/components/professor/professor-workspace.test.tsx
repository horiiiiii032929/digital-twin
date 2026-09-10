import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactElement } from 'react'
import { createHookHarness } from '@/hooks/testing/hook-harness'
import type { OnboardingController } from '@/hooks/use-onboarding-session'

const h = vi.hoisted(() => ({ current: null as ReturnType<typeof createHookHarness> | null }))
vi.mock('react', () => ({
  useState: (...args: [unknown]) => h.current!.react.useState(...args),
  useCallback: (...args: [unknown, unknown[]]) => h.current!.react.useCallback(...args),
  useEffect: (...args: [() => void | (() => void), unknown[]]) => h.current!.react.useEffect(...args),
}))
vi.mock('@/components/onboarding/console/professor-review-console', () => ({ ProfessorReviewConsole: () => null }))
vi.mock('@/components/professor/professor-delivery-workspace', () => ({ ProfessorDeliveryWorkspace: () => null }))
import { ProfessorWorkspace } from './professor-workspace'

type ViewProps = {
  initialCourseId?: string | null
  onCourseChange: (id: string) => void
  onOpenSetup: () => void
  onOpenDelivery: () => void
}
const render = () => h.current!.render(() => ProfessorWorkspace({controller: {} as OnboardingController})) as ReactElement<ViewProps>

beforeEach(() => {
  h.current = createHookHarness()
  vi.stubGlobal('document', { title: '' })
  vi.stubGlobal('window', { location: { pathname: '/professor/delivery' },
    history: { pushState: vi.fn() }, addEventListener: vi.fn(), removeEventListener: vi.fn() })
})

describe('professor delivery and setup navigation', () => {
  it('returns to the chosen course after reviewing setup', () => {
    let view = render()
    view.props.onCourseChange('course-b')
    view = render()
    view.props.onOpenSetup()
    view = render()
    view.props.onOpenDelivery()
    view = render()
    expect(view.props.initialCourseId).toBe('course-b')
    expect(window.history.pushState).toHaveBeenLastCalledWith({}, '', '/professor/delivery')
  })

  it('does not carry a prior professor selection into a fresh account workspace', () => {
    render().props.onCourseChange('private-course-a')
    render()
    h.current = createHookHarness()
    expect(render().props.initialCourseId).toBeNull()
  })
})

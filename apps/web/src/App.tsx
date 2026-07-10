import { ProfessorReviewConsole } from "@/components/onboarding/console/professor-review-console"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"

function App() {
  const controller = useOnboardingSession()

  return <ProfessorReviewConsole controller={controller} />
}

export default App

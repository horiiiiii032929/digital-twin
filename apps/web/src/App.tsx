import { useEffect } from "react"

import { ProfessorReviewConsole } from "@/components/onboarding/console/professor-review-console"
import { StudentWorkspace } from "@/components/student/student-workspace"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"
import { useStudentWorkspace } from "@/hooks/use-student-workspace"

function App() {
  if (window.location.pathname.startsWith("/student")) {
    return <StudentApp />
  }

  return <ProfessorApp />
}

function ProfessorApp() {
  const controller = useOnboardingSession()
  useDocumentTitle("Professor Review Console · Course Digital Twin")
  return <ProfessorReviewConsole controller={controller} />
}

function StudentApp() {
  const controller = useStudentWorkspace()
  useDocumentTitle("Student Tutor · Course Digital Twin")
  return <StudentWorkspace controller={controller} />
}

function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title
  }, [title])
}

export default App

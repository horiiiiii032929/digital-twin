import { useEffect } from "react"

import { AccountControl } from "@/components/auth/account-control"
import { AdminWorkspace } from "@/components/auth/admin-workspace"
import { LoginScreen } from "@/components/auth/login-screen"
import { ProfessorWorkspace } from "@/components/professor/professor-workspace"
import { StudentWorkspace } from "@/components/student/student-workspace"
import { useAuthSession } from "@/hooks/use-auth-session"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"
import { useStudentWorkspace } from "@/hooks/use-student-workspace"

function App() {
  if (import.meta.env.VITE_AUTH_MODE === "session") {
    return <AuthenticatedApp />
  }

  if (window.location.pathname.startsWith("/student")) {
    return <StudentApp />
  }

  return <ProfessorApp />
}

function AuthenticatedApp() {
  const auth = useAuthSession()

  if (auth.loading) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-[var(--shell)]">
        <p className="text-sm text-muted-foreground" role="status">
          Checking your session…
        </p>
      </main>
    )
  }

  if (!auth.profile) {
    return (
      <LoginScreen
        error={auth.error}
        onSubmit={auth.signIn}
        submitting={auth.submitting}
      />
    )
  }

  return (
    <>
      {auth.profile.role === "student" ? <StudentApp /> : null}
      {auth.profile.role === "professor" ? <ProfessorApp /> : null}
      {auth.profile.role === "admin" ? <AdminWorkspace /> : null}
      <AccountControl
        onChangePassword={auth.updatePassword}
        onSignOut={auth.signOut}
        profile={auth.profile}
        submitting={auth.submitting}
      />
    </>
  )
}

function ProfessorApp() {
  const supervisorDemo =
    new URLSearchParams(window.location.search).get("demo") === "supervisor"
  const controller = useOnboardingSession({ supervisorDemo })
  return (
    <ProfessorWorkspace
      controller={controller}
      supervisorDemo={supervisorDemo}
    />
  )
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

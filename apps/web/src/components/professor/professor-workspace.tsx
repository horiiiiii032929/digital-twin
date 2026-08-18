import { useCallback, useEffect, useState } from "react"

import { ProfessorReviewConsole } from "@/components/onboarding/console/professor-review-console"
import { ProfessorDeliveryWorkspace } from "@/components/professor/professor-delivery-workspace"
import type { OnboardingController } from "@/hooks/use-onboarding-session"

export function ProfessorWorkspace({
  controller,
  supervisorDemo = false,
}: {
  controller: OnboardingController
  supervisorDemo?: boolean
}) {
  const [view, setView] = useState<"setup" | "delivery">(viewFromLocation)

  const navigate = useCallback((next: "setup" | "delivery") => {
    window.history.pushState(
      {},
      "",
      next === "delivery" ? "/professor/delivery" : "/professor/setup",
    )
    setView(next)
  }, [])

  useEffect(() => {
    document.title =
      view === "delivery"
        ? "Course Delivery · Course Digital Twin"
        : "Professor Review Console · Course Digital Twin"
    const onPopState = () => setView(viewFromLocation())
    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [view])

  if (view === "delivery") {
    return (
      <ProfessorDeliveryWorkspace
        controller={controller}
        onOpenSetup={() => navigate("setup")}
      />
    )
  }

  return (
    <ProfessorReviewConsole
      controller={controller}
      supervisorDemo={supervisorDemo}
      onOpenDelivery={
        supervisorDemo ? undefined : () => navigate("delivery")
      }
    />
  )
}

function viewFromLocation(): "setup" | "delivery" {
  return window.location.pathname.startsWith("/professor/delivery")
    ? "delivery"
    : "setup"
}

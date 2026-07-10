import type {
  OnboardingSession,
  ReleaseStatus,
} from "@/lib/api/types"

export type ReleaseReadiness = {
  status: ReleaseStatus
  blockers: string[]
  approvedSources: number
  policyBlockers: number
  previewCount: number
  acceptedPreviews: number
  pendingPreviews: number
  checklistBlockers: number
}

export type StepState = {
  id: "sources" | "interview" | "policy" | "preview" | "approval"
  label: string
  detail: string
  state: "active" | "blocked" | "complete" | "waiting"
}

export function getReleaseReadiness(
  session: OnboardingSession | null,
): ReleaseReadiness {
  const blockers = new Set(Object.values(session?.release_blockers ?? {}).flat())
  if (!session) {
    blockers.add("Start the onboarding session.")
  } else {
    if (session.source_inventory.length === 0) {
      blockers.add("Add at least one approved source metadata item.")
    }
    if (!session.policy) {
      blockers.add("Complete the instructor interview to generate policy.")
    }
    if (session.policy && session.preview_cases.length === 0) {
      blockers.add("Generate preview evidence for professor review.")
    }
    if (session.policy && session.approval_checklist.length === 0) {
      blockers.add("Generate the approval checklist.")
    }
  }

  const approvedSources =
    session?.source_inventory.filter(
      (source) => source.permission_status === "approved" && !source.excluded,
    ).length ?? 0
  const policyFields = session?.policy
    ? [
        ...session.policy.safety_compliance,
        ...session.policy.pedagogy,
        ...session.policy.professor_review,
      ]
    : []
  const policyBlockers = policyFields.filter(
    (field) => field.status === "blocks_release",
  ).length
  const previewCount = session?.preview_cases.length ?? 0
  const acceptedPreviews =
    session?.preview_cases.filter((preview) => preview.decision === "accepted")
      .length ?? 0
  const pendingPreviews =
    session?.preview_cases.filter((preview) => preview.decision !== "accepted")
      .length ?? 0
  const checklistBlockers =
    session?.approval_checklist.filter(
      (item) => item.blocks_release && !item.checked,
    ).length ?? 0

  return {
    status: session?.policy?.release_status ?? "draft",
    blockers: [...blockers],
    approvedSources,
    policyBlockers,
    previewCount,
    acceptedPreviews,
    pendingPreviews,
    checklistBlockers,
  }
}

export function getStepStates(session: OnboardingSession | null): StepState[] {
  const currentStep = session?.current_step ?? "starting"
  const hasPolicy = Boolean(session?.policy)
  const hasSources = (session?.source_inventory.length ?? 0) > 0
  const sourceBlocked =
    (session?.release_blockers.source_inventory?.length ?? 0) > 0
  const previewBlocked =
    (session?.release_blockers.preview_acceptance?.length ?? 0) > 0
  const checklistBlocked =
    (session?.release_blockers.approval_checklist?.length ?? 0) > 0

  return [
    {
      id: "sources",
      label: "Source inventory",
      detail: hasSources
        ? "Metadata added for review."
        : "Add approved source metadata.",
      state: sourceBlocked ? "blocked" : hasSources ? "complete" : "waiting",
    },
    {
      id: "interview",
      label: "Instructor interview",
      detail: hasPolicy
        ? "Answers generated a draft policy."
        : `Current: ${formatStep(currentStep)}`,
      state: hasPolicy ? "complete" : "active",
    },
    {
      id: "policy",
      label: "Tutor policy",
      detail: hasPolicy
        ? "Review editable policy fields."
        : "Generated after interview.",
      state: hasPolicy ? "active" : "waiting",
    },
    {
      id: "preview",
      label: "Preview evidence",
      detail: previewBlocked
        ? "Accept or revise required cases."
        : "Compare configured and generic responses.",
      state: previewBlocked
        ? "blocked"
        : (session?.preview_cases.length ?? 0) > 0
          ? "complete"
          : "waiting",
    },
    {
      id: "approval",
      label: "Professor approval",
      detail: checklistBlocked
        ? "Checklist still blocks release."
        : "Final release confirmation.",
      state: checklistBlocked
        ? "blocked"
        : session?.policy?.release_status === "approved"
          ? "complete"
          : "waiting",
    },
  ]
}

export function getNextAction(
  session: OnboardingSession | null,
  blockers: string[],
): { title: string; detail: string } {
  if (!session) {
    return {
      title: "Starting onboarding session",
      detail:
        "The review console will populate once the API returns the draft session.",
    }
  }

  if (blockers.length === 0 && session.policy?.release_status === "approved") {
    return {
      title: "Release gate is clear",
      detail: "All professor review gates are complete for this draft.",
    }
  }

  if (session.source_inventory.length === 0) {
    return {
      title: "Add source metadata first",
      detail:
        "Start with syllabus, slide, assignment, or rubric metadata so preview grounding can be audited.",
    }
  }

  if (!session.policy) {
    return {
      title: "Continue the instructor interview",
      detail: `Answer the current prompt for ${formatStep(session.current_step)} to generate the first tutor policy draft.`,
    }
  }

  if (session.revision_proposal) {
    return {
      title: "Resolve the pending revision",
      detail:
        "A professor feedback item has produced a policy update proposal that needs confirmation or discard.",
    }
  }

  if (blockers.length > 0) {
    return {
      title: "Clear the next release blocker",
      detail: blockers[0],
    }
  }

  return {
    title: "Review final approval",
    detail:
      "The draft is ready for professor approval once the checklist confirms the release criteria.",
  }
}

export function formatReleaseStatus(status: ReleaseStatus): string {
  if (status === "approved") {
    return "approved"
  }
  if (status === "blocked") {
    return "blocked"
  }
  return "draft only"
}

export function formatStep(step: string): string {
  return step.replaceAll("_", " ")
}

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

export type ReviewStageId =
  | "sources"
  | "interview"
  | "policy"
  | "preview"
  | "approval"

export type StepState = {
  id: ReviewStageId
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
    const hasApprovedSource = session.source_inventory.some(
      (source) => source.permission_status === "approved" && !source.excluded,
    )
    if (!hasApprovedSource) {
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
  const hasSources =
    session?.source_inventory.some(
      (source) => source.permission_status === "approved" && !source.excluded,
    ) ?? false
  const sourceBlocked =
    (session?.release_blockers.source_inventory?.length ?? 0) > 0 ||
    Boolean(session && !hasSources)
  const policyFields = session?.policy
    ? [
        ...session.policy.safety_compliance,
        ...session.policy.pedagogy,
        ...session.policy.professor_review,
      ]
    : []
  const policyBlocked = policyFields.some(
    (field) => field.status === "blocks_release",
  )
  const previewBlocked =
    (session?.release_blockers.preview_acceptance?.length ?? 0) > 0 ||
    (session?.preview_cases.some(
      (preview) => preview.decision !== "accepted",
    ) ?? false)
  const checklistBlocked =
    (session?.release_blockers.approval_checklist?.length ?? 0) > 0 ||
    (session?.approval_checklist.some(
      (item) => item.blocks_release && !item.checked,
    ) ?? false)

  return [
    {
      id: "sources",
      label: "Sources",
      detail: hasSources
        ? "Metadata added for review."
        : "Add approved source metadata.",
      state: sourceBlocked ? "blocked" : hasSources ? "complete" : "waiting",
    },
    {
      id: "interview",
      label: "Interview",
      detail: hasPolicy
        ? "Answers generated a draft policy."
        : `Current: ${formatStep(currentStep)}`,
      state: hasPolicy ? "complete" : "active",
    },
    {
      id: "policy",
      label: "Policy",
      detail: hasPolicy
        ? "Review editable policy fields."
        : "Generated after interview.",
      state: !hasPolicy ? "waiting" : policyBlocked ? "blocked" : "active",
    },
    {
      id: "preview",
      label: "Preview",
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
      label: "Approval",
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
): { title: string; detail: string; stage: ReviewStageId } {
  if (!session) {
    return {
      title: "Starting onboarding session",
      detail:
        "The review console will populate once the API returns the draft session.",
      stage: "interview",
    }
  }

  if (blockers.length === 0 && session.policy?.release_status === "approved") {
    return {
      title: "Release gate is clear",
      detail: "All professor review gates are complete for this draft.",
      stage: "approval",
    }
  }

  if (session.source_inventory.length === 0) {
    return {
      title: "Add source metadata first",
      detail:
        "Start with syllabus, slide, assignment, or rubric metadata so preview grounding can be audited.",
      stage: "sources",
    }
  }

  const hasApprovedSource = session.source_inventory.some(
    (source) => source.permission_status === "approved" && !source.excluded,
  )
  if (!hasApprovedSource) {
    return {
      title: "Approve a course source",
      detail:
        "At least one registered source must be explicitly approved and included before the release gate can clear.",
      stage: "sources",
    }
  }

  if (!session.policy) {
    return {
      title: "Continue the instructor interview",
      detail: `Answer the current prompt for ${formatStep(session.current_step)} to generate the first tutor policy draft.`,
      stage: "interview",
    }
  }

  if (session.revision_proposal) {
    return {
      title: "Resolve the pending revision",
      detail:
        "A professor feedback item has produced a policy update proposal that needs confirmation or discard.",
      stage: "preview",
    }
  }

  const policyFields = [
    ...session.policy.safety_compliance,
    ...session.policy.pedagogy,
    ...session.policy.professor_review,
  ]
  if (policyFields.some((field) => field.status === "blocks_release")) {
    return {
      title: "Resolve blocking policy fields",
      detail:
        "Review the fields marked as release blockers and either confirm their values or retain an explicit safe default.",
      stage: "policy",
    }
  }

  if (session.preview_cases.some((preview) => preview.decision !== "accepted")) {
    return {
      title: "Review required preview evidence",
      detail:
        "Every required preview needs an explicit professor decision before approval.",
      stage: "preview",
    }
  }

  if (
    session.approval_checklist.some(
      (item) => item.blocks_release && !item.checked,
    )
  ) {
    return {
      title: "Complete the approval checklist",
      detail:
        "Confirm each remaining release condition after its supporting evidence is clear.",
      stage: "approval",
    }
  }

  if (blockers.length > 0) {
    return {
      title: "Clear the next release blocker",
      detail: blockers[0],
      stage: stageForBlocker(blockers[0]),
    }
  }

  return {
    title: "Review final approval",
    detail:
      "The draft is ready for professor approval once the checklist confirms the release criteria.",
    stage: "approval",
  }
}

function stageForBlocker(blocker: string): ReviewStageId {
  const normalized = blocker.toLowerCase()

  if (
    normalized.includes("source inventory") ||
    normalized.includes("approved source metadata")
  ) {
    return "sources"
  }
  if (normalized.includes("preview") || normalized.includes("evidence")) {
    return "preview"
  }
  if (normalized.includes("policy") || normalized.includes("interview")) {
    return "policy"
  }
  return "approval"
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

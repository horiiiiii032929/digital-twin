import type { ProfessorTeachingProfilePreview } from "@/lib/api/types"

export function canApproveTeachingProfilePreview(
  profileId: string,
  preview: ProfessorTeachingProfilePreview | null,
): preview is ProfessorTeachingProfilePreview {
  return Boolean(
    preview
      && preview.profile_id === profileId
      && preview.cases.length === 10
      && preview.preview_sha256.trim(),
  )
}

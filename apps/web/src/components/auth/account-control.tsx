import { useState, type FormEvent } from "react"
import { KeyRound, LogOut, UserRound } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { IdentityProfile } from "@/lib/api/types"

export function AccountControl({
  profile,
  submitting,
  onSignOut,
  onChangePassword,
}: {
  profile: IdentityProfile
  submitting: boolean
  onSignOut: () => Promise<void>
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<void>
}) {
  const [error, setError] = useState<string | null>(null)

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const next = String(form.get("new_password") ?? "")
    if (next !== String(form.get("confirm_password") ?? "")) {
      setError("New passwords do not match.")
      return
    }
    setError(null)
    try {
      await onChangePassword(String(form.get("current_password") ?? ""), next)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Password change failed.")
    }
  }

  return (
    <details className="group fixed top-3 right-3 z-50">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl border bg-white/95 p-1.5 pl-3 shadow-sm backdrop-blur marker:hidden">
        <div className="hidden min-w-0 text-right sm:block">
          <p className="max-w-40 truncate text-xs font-medium">
            {profile.display_name}
          </p>
          <p className="text-[0.68rem] capitalize text-muted-foreground">
            {profile.role}
          </p>
        </div>
        <span className="flex size-7 items-center justify-center rounded-md bg-muted">
          <UserRound className="size-3.5" aria-hidden="true" />
        </span>
      </summary>

      <div className="absolute top-[calc(100%+0.5rem)] right-0 w-[min(22rem,calc(100vw-1.5rem))] rounded-xl border bg-white p-4 shadow-lg">
        <p className="text-sm font-semibold">Account security</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {profile.email}
        </p>
        <form className="mt-4 space-y-3" onSubmit={submitPassword}>
          <PasswordField label="Current password" name="current_password" />
          <PasswordField label="New password" name="new_password" />
          <PasswordField label="Confirm new password" name="confirm_password" />
          {error ? (
            <p className="text-xs leading-5 text-destructive" role="alert">
              {error}
            </p>
          ) : null}
          <Button className="w-full" disabled={submitting} size="sm" type="submit">
            <KeyRound aria-hidden="true" />
            Change password
          </Button>
        </form>
        <div className="my-4 border-t" />
        <Button
          className="w-full"
          disabled={submitting}
          onClick={() => void onSignOut()}
          size="sm"
          variant="outline"
        >
          <LogOut aria-hidden="true" />
          Sign out
        </Button>
      </div>
    </details>
  )
}

function PasswordField({ label, name }: { label: string; name: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium">{label}</span>
      <input
        autoComplete={name === "current_password" ? "current-password" : "new-password"}
        className="h-9 w-full rounded-md border px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
        minLength={name === "current_password" ? 1 : 12}
        name={name}
        required
        type="password"
      />
    </label>
  )
}

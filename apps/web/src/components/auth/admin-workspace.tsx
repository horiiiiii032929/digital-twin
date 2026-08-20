import { useState, type FormEvent } from "react"
import { CheckCircle2, UserPlus } from "lucide-react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { WorkspaceBrand } from "@/components/workspace/workspace-brand"
import { inviteAccount } from "@/lib/api"
import type { AccountRole, IdentityProfile } from "@/lib/api/types"

export function AdminWorkspace() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<IdentityProfile | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    setSubmitting(true)
    setError(null)
    setCreated(null)
    try {
      const account = await inviteAccount({
        email: String(form.get("email") ?? ""),
        display_name: String(form.get("display_name") ?? ""),
        role: String(form.get("role") ?? "student") as AccountRole,
        temporary_password: String(form.get("temporary_password") ?? ""),
      })
      setCreated(account)
      formElement.reset()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Invite failed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-dvh bg-[var(--shell)]">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center px-5 sm:px-8">
          <WorkspaceBrand className="border-0 px-0" />
          <span className="ml-auto rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
            Administration
          </span>
        </div>
      </header>
      <section className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-[var(--accent-strong)]">
            Invite-only access
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em]">
            Add a professor or student
          </h1>
          <p className="mt-3 leading-7 text-muted-foreground">
            Accounts receive only the workspace allowed by their role. Share the
            temporary password through a separate trusted channel.
          </p>
        </div>

        <Card className="mt-8 max-w-2xl">
          <CardHeader>
            <CardTitle>New account</CardTitle>
            <CardDescription>
              Every account can be disabled and every session can be revoked.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-5 sm:grid-cols-2" onSubmit={submit}>
              <AdminField label="Display name" maxLength={160} name="display_name" />
              <AdminField label="Email" maxLength={320} name="email" type="email" />
              <label className="block">
                <span className="mb-2 block text-sm font-medium">Role</span>
                <select
                  className="h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
                  defaultValue="student"
                  name="role"
                >
                  <option value="student">Student</option>
                  <option value="professor">Professor</option>
                  <option value="admin">Administrator</option>
                </select>
              </label>
              <AdminField
                autoComplete="new-password"
                label="Temporary password"
                minLength={12}
                maxLength={1024}
                name="temporary_password"
                type="password"
              />

              {error ? (
                <Alert className="sm:col-span-2" variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}
              {created ? (
                <Alert className="border-[var(--success-border)] bg-[var(--success-soft)] text-[var(--success)] sm:col-span-2">
                  <CheckCircle2 aria-hidden="true" />
                  <AlertDescription className="text-[var(--success)]">
                    <p>{created.display_name} was invited as {created.role}.</p>
                    <p className="mt-1">
                      Account ID: {" "}
                      <code className="break-all font-mono font-semibold select-all">
                        {created.account_id}
                      </code>
                    </p>
                  </AlertDescription>
                </Alert>
              ) : null}

              <div className="sm:col-span-2">
                <Button disabled={submitting} type="submit">
                  <UserPlus aria-hidden="true" />
                  {submitting ? "Creating account…" : "Create account"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  )
}

function AdminField({
  label,
  ...props
}: { label: string } & React.ComponentProps<"input">) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium">{label}</span>
      <input
        className="h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
        required
        {...props}
      />
    </label>
  )
}

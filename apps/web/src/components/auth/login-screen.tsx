import { useState, type FormEvent } from "react"
import { ArrowRight, LockKeyhole } from "lucide-react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { WorkspaceBrand } from "@/components/workspace/workspace-brand"

type LoginScreenProps = {
  error: string | null
  submitting: boolean
  onSubmit: (email: string, password: string) => Promise<void>
}

export function LoginScreen({ error, submitting, onSubmit }: LoginScreenProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onSubmit(email, password)
  }

  return (
    <main className="grid min-h-dvh bg-[var(--shell)] lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.72fr)]">
      <section className="hidden border-r bg-white p-10 lg:flex lg:flex-col lg:justify-between">
        <WorkspaceBrand className="border-0 px-0" />
        <div className="max-w-xl pb-[12vh]">
          <p className="mb-4 text-sm font-medium text-[var(--accent-strong)]">
            Course-grounded teaching, with oversight
          </p>
          <h1 className="text-5xl leading-[1.05] font-semibold tracking-[-0.045em] text-balance">
            One trusted workspace for professors and students.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-muted-foreground">
            Configure teaching behavior, publish reviewed course evidence, and
            answer student questions with inspectable citations.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Invite-only access · Course-scoped evidence · Revocable sessions
        </p>
      </section>

      <section className="flex min-h-dvh items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <WorkspaceBrand className="mb-10 border-0 px-0 lg:hidden" />
          <Card className="gap-0 py-0 shadow-sm ring-black/10">
            <CardContent className="p-6 sm:p-8">
              <span className="mb-6 flex size-10 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                <LockKeyhole className="size-5" aria-hidden="true" />
              </span>
              <h2 className="text-2xl font-semibold tracking-[-0.025em]">
                Sign in to your workspace
              </h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Use the email address and temporary password from your invite.
              </p>

              <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Email</span>
                  <input
                    autoComplete="email"
                    autoFocus
                    className="h-11 w-full rounded-lg border bg-white px-3.5 text-sm outline-none transition focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
                    name="email"
                    maxLength={320}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    type="email"
                    value={email}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Password</span>
                  <input
                    autoComplete="current-password"
                    className="h-11 w-full rounded-lg border bg-white px-3.5 text-sm outline-none transition focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
                    name="password"
                    maxLength={1024}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    type="password"
                    value={password}
                  />
                </label>

                {error ? (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ) : null}

                <Button
                  className="w-full"
                  disabled={submitting}
                  size="lg"
                  type="submit"
                >
                  {submitting ? "Signing in…" : "Sign in"}
                  {!submitting ? <ArrowRight aria-hidden="true" /> : null}
                </Button>
              </form>
            </CardContent>
          </Card>
          <p className="mt-5 text-center text-xs leading-5 text-muted-foreground">
            Access is provisioned by the project administrator. Contact them if
            your invite has expired.
          </p>
        </div>
      </section>
    </main>
  )
}

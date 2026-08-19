import { request } from "@/lib/api/client"
import type { AccountRole, IdentityProfile } from "@/lib/api/types"

export function login(
  email: string,
  password: string,
): Promise<IdentityProfile> {
  return request<IdentityProfile>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export function getCurrentSession(): Promise<IdentityProfile> {
  return request<IdentityProfile>("/api/auth/session")
}

export function logout(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" })
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  return request<void>("/api/auth/password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}

export function inviteAccount(payload: {
  email: string
  display_name: string
  role: AccountRole
  temporary_password: string
}): Promise<IdentityProfile> {
  return request<IdentityProfile>("/api/admin/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

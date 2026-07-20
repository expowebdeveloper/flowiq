import { loanTypeLabel } from "@/features/loans/loanTypeMeta"

const STORAGE_KEY = "flowiq.loan_apply.saved_applicants"
const MAX_SAVED = 20

/**
 * Snapshot of a submitted loan-apply form, minus `ssn` — this is saved to
 * localStorage (this browser only, no backend/auth involved, since the form
 * is public and unauthenticated) purely so a returning applicant can pick
 * their name from the First Name field's datalist and have every other
 * field prefilled instead of retyping the whole form. SSN is deliberately
 * never saved/prefilled: unlike the other fields, it's sensitive enough that
 * sitting in plaintext localStorage indefinitely on a public form isn't
 * worth the convenience, so it's always re-entered fresh.
 */
export type SavedApplicant = {
  saved_at: string
  first_name: string
  last_name: string
  email: string
  phone_number: string
  date_of_birth: string
  gender: string
  citizenship_status: string
  current_address: string
  marital_status: string
  fico_score: string
  loan_type: string
  loan_amount: string
  zip_code: string
  extra_loan_details: Record<string, string>
}

function readAll(): SavedApplicant[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(applicants: SavedApplicant[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(applicants))
  } catch {
    // Storage full/unavailable (private browsing, quota) — prefill is a
    // convenience feature, so just drop the save rather than surface an error.
  }
}

export function listSavedApplicants(): SavedApplicant[] {
  return readAll().sort((a, b) => new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime())
}

/** Display label for the First Name datalist, e.g. "Jane — Home Loan (jane@x.com)". */
export function savedApplicantLabel(applicant: SavedApplicant): string {
  return `${applicant.first_name} — ${loanTypeLabel(applicant.loan_type)} (${applicant.email})`
}

/**
 * Saves (or updates, matched by email — the closest thing to a stable
 * identity this public form has) a submitted form's data, excluding ssn.
 * Capped at MAX_SAVED entries, oldest dropped first, so this can't grow
 * unbounded over many submissions from the same browser.
 */
export function saveApplicant(values: Omit<SavedApplicant, "saved_at">) {
  const existing = readAll().filter((a) => a.email.toLowerCase() !== values.email.toLowerCase())
  const next = [{ ...values, saved_at: new Date().toISOString() }, ...existing].slice(0, MAX_SAVED)
  writeAll(next)
}

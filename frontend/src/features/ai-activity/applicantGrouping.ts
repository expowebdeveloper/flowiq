import type { AiActivityEvent } from "@/services/aiActivityService"

export interface ApplicantGroup {
  submissionId: string
  events: AiActivityEvent[] // newest first
  latestAt: string
}

/**
 * Splits the flat activity feed into one group per applicant (submission_id)
 * plus a separate "unscoped" bucket for events with no submission_id (bare
 * mailbox_poll summaries like "found N new replies", which aren't tied to
 * any one applicant). Groups are ordered by their most recent event, newest
 * applicant first — this is what lets the page show "whose pipeline is
 * this" instead of one flat mixed feed.
 */
export function groupEventsByApplicant(events: AiActivityEvent[]): {
  groups: ApplicantGroup[]
  unscoped: AiActivityEvent[]
} {
  const bySubmission = new Map<string, AiActivityEvent[]>()
  const unscoped: AiActivityEvent[] = []

  for (const event of events) {
    if (!event.submission_id) {
      unscoped.push(event)
      continue
    }
    const existing = bySubmission.get(event.submission_id)
    if (existing) existing.push(event)
    else bySubmission.set(event.submission_id, [event])
  }

  const groups: ApplicantGroup[] = Array.from(bySubmission.entries()).map(([submissionId, evs]) => ({
    submissionId,
    events: evs, // already newest-first since `events` is newest-first
    latestAt: evs[0].created_at,
  }))

  groups.sort((a, b) => new Date(b.latestAt).getTime() - new Date(a.latestAt).getTime())

  return { groups, unscoped }
}

export interface ApplicantIssue {
  message: string
  detail: Record<string, unknown> | null
}

/**
 * Surfaces the most relevant reason an applicant's pipeline currently needs
 * attention. Two cases:
 *
 * 1. An explicit "error" event on any source — always worth flagging,
 *    however old, since nothing else in the pipeline supersedes a failed
 *    send/notify.
 * 2. document_processing whose MOST RECENT event (not just any past one) is
 *    "info" — that status means missing/unverified documents (see
 *    loan_apply/document_processing.py's emit call). Only the latest
 *    document_processing event matters here: an applicant who was
 *    incomplete on their first reply but later sent everything has a
 *    later "success" event that supersedes the earlier "info", so the
 *    banner must not resurface that resolved issue.
 */
export function findApplicantIssue(eventsNewestFirst: AiActivityEvent[]): ApplicantIssue | null {
  const errorEvent = eventsNewestFirst.find((e) => e.status === "error")
  if (errorEvent) return { message: errorEvent.message, detail: errorEvent.detail }

  const latestDocEvent = eventsNewestFirst.find((e) => e.source === "document_processing")
  if (latestDocEvent && latestDocEvent.status === "info") {
    return { message: latestDocEvent.message, detail: latestDocEvent.detail }
  }

  return null
}

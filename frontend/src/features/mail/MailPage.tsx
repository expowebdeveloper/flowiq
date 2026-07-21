import { useEffect, useRef, useState } from "react"
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Inbox as InboxIcon,
  Loader2,
  Pencil,
  Paperclip,
  RefreshCw,
  Send as SendIcon,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useAuth } from "@/contexts/AuthContext"
import { API_BASE_URL } from "@/services/apiClient"
import { inboundService } from "@/services/inboundService"
import { outboundService } from "@/services/outboundService"
import { loanApplyService } from "@/services/loanApplyService"
import type { EmailAttachment, InboxFullMessage, InboxMessageSummary } from "@/types/api"

const IMAGE_MIME_TYPES = new Set(["image/jpeg", "image/png", "image/gif", "image/webp"])

function AttachmentList({ attachments }: { attachments: EmailAttachment[] }) {
  if (attachments.length === 0) return null
  return (
    <div className="flex flex-wrap gap-3 border-t border-border pt-3">
      {attachments.map((att, i) => {
        const url = `${API_BASE_URL}${att.download_url}`
        if (IMAGE_MIME_TYPES.has(att.mime_type)) {
          return (
            <a
              key={`${att.filename}-${i}`}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="block overflow-hidden rounded-lg border border-border transition-opacity hover:opacity-90"
            >
              <img src={url} alt={att.filename} className="max-h-64 max-w-xs object-contain" />
              <div className="truncate border-t border-border px-2 py-1 text-xs text-muted-foreground">
                {att.filename}
              </div>
            </a>
          )
        }
        return (
          <a
            key={`${att.filename}-${i}`}
            href={url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent/50"
          >
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="max-w-[12rem] truncate">{att.filename}</span>
            <Download className="size-3.5 shrink-0 text-muted-foreground" />
          </a>
        )
      })}
    </div>
  )
}

let entityDecoderEl: HTMLTextAreaElement | null = null

/** Gmail snippets/metadata headers come HTML-entity-encoded (e.g. "&#39;", "&amp;") — decode for plain-text display. */
function decodeHtmlEntities(text: string): string {
  if (!text) return text
  if (!entityDecoderEl) entityDecoderEl = document.createElement("textarea")
  entityDecoderEl.innerHTML = text
  return entityDecoderEl.value
}

type Folder = "inbox" | "sent"

/**
 * Mail should only show correspondence with loan applicants (people who
 * submitted the /loan-apply form), not the whole linked mailbox. Gmail search
 * operators: inbox mail is scoped by sender (from:), sent mail by recipient (to:).
 */
function buildFolderQuery(folder: Folder, applicantEmails: string[]): string {
  const base = folder === "inbox" ? "in:inbox" : "in:sent"
  if (applicantEmails.length === 0) return base
  const operator = folder === "inbox" ? "from" : "to"
  const addresses = applicantEmails.map((e) => `${operator}:${e}`).join(" OR ")
  return `${base} (${addresses})`
}

const PAGE_SIZE = 25

/**
 * Collapses a flat page of messages into one row per Gmail thread_id, so an
 * applicant's whole back-and-forth (requirements email + every reply/follow-up)
 * shows as a single conversation instead of one row per individual message.
 * Keeps the most recent message per thread for the row's preview, and the
 * count of messages in that thread. Order follows first-seen thread order,
 * which — since `messages` arrives newest-first from Gmail — is already
 * most-recent-thread-first.
 */
function groupByThread(messages: InboxMessageSummary[]): { thread: InboxMessageSummary; count: number }[] {
  const order: string[] = []
  const latest = new Map<string, InboxMessageSummary>()
  const counts = new Map<string, number>()

  for (const m of messages) {
    const key = m.thread_id || m.id
    if (!latest.has(key)) {
      order.push(key)
      latest.set(key, m)
      counts.set(key, 1)
    } else {
      counts.set(key, (counts.get(key) ?? 1) + 1)
      // messages arrive newest-first, so the first one seen per thread is
      // already the most recent — no need to compare dates here.
    }
  }

  return order.map((key) => ({ thread: latest.get(key)!, count: counts.get(key)! }))
}

interface PageState {
  messages: InboxMessageSummary[]
  isLoading: boolean
  errorMessage: string | null
  pageIndex: number
  // tokens[i] = the page_token that produced page i; tokens[0] is always undefined (first page)
  tokens: (string | undefined)[]
  nextPageToken: string | null
}

function emptyPageState(): PageState {
  return {
    messages: [],
    isLoading: false,
    errorMessage: null,
    pageIndex: 0,
    tokens: [undefined],
    nextPageToken: null,
  }
}

function FolderButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean
  icon: typeof InboxIcon
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-full px-4 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary/15 text-primary"
          : "text-foreground/80 hover:bg-accent",
      )}
    >
      <Icon className="size-4 shrink-0" />
      <span className="flex-1 text-left">{label}</span>
    </button>
  )
}

export function MailPage() {
  const { email } = useAuth()
  const [folder, setFolder] = useState<Folder>("inbox")
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [isComposeOpen, setIsComposeOpen] = useState(false)
  const [applicantEmails, setApplicantEmails] = useState<string[] | null>(null)

  const [pages, setPages] = useState<Record<Folder, PageState>>({
    inbox: emptyPageState(),
    sent: emptyPageState(),
  })

  const requestSeq = useRef<Record<Folder, number>>({ inbox: 0, sent: 0 })
  const pagesRef = useRef(pages)
  pagesRef.current = pages

  useEffect(() => {
    loanApplyService.getApplicantEmails().then((res) => {
      setApplicantEmails(res.ok && res.data ? res.data : [])
    })
  }, [])

  async function loadPage(targetFolder: Folder, pageIndex: number) {
    if (!email || applicantEmails === null) return
    if (pagesRef.current[targetFolder].isLoading) return // avoid concurrent requests desyncing tokens
    const seq = ++requestSeq.current[targetFolder]
    const pageToken = pagesRef.current[targetFolder].tokens[pageIndex]
    setPages((prev) => ({
      ...prev,
      [targetFolder]: { ...prev[targetFolder], isLoading: true, errorMessage: null },
    }))

    const res = await inboundService.getInbox({
      email,
      query: buildFolderQuery(targetFolder, applicantEmails),
      max_results: PAGE_SIZE,
      page_token: pageToken,
    })

    if (seq !== requestSeq.current[targetFolder]) return // stale response, a newer request superseded it

    setPages((prev) => {
      const current = prev[targetFolder]
      if (!res.ok || !res.data) {
        return {
          ...prev,
          [targetFolder]: {
            ...current,
            isLoading: false,
            errorMessage: res.errorMessage ?? "Failed to load messages",
          },
        }
      }
      const nextTokens = [...current.tokens]
      if (res.data.next_page_token) nextTokens[pageIndex + 1] = res.data.next_page_token
      return {
        ...prev,
        [targetFolder]: {
          ...current,
          isLoading: false,
          errorMessage: null,
          messages: res.data.messages,
          pageIndex,
          tokens: nextTokens,
          nextPageToken: res.data.next_page_token,
        },
      }
    })
  }

  useEffect(() => {
    if (!email || applicantEmails === null) return
    if (pages[folder].messages.length === 0 && !pages[folder].isLoading) {
      loadPage(folder, 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email, folder, applicantEmails])

  if (!email || applicantEmails === null) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" /> Loading your account…
      </div>
    )
  }

  const state = pages[folder]
  const hasNext = Boolean(state.nextPageToken)
  const hasPrev = state.pageIndex > 0
  const rangeStart = state.messages.length ? state.pageIndex * PAGE_SIZE + 1 : 0
  const rangeEnd = state.pageIndex * PAGE_SIZE + state.messages.length
  const threadRows = groupByThread(state.messages)

  return (
    <div className="flex h-[calc(100svh_-_6rem)] gap-6">
      {/* Left rail */}
      <div className="hidden w-56 shrink-0 flex-col gap-4 md:flex">
        <Button className="h-12 w-full justify-start gap-2 rounded-2xl shadow-sm" onClick={() => setIsComposeOpen(true)}>
          <Pencil className="size-4" /> Compose
        </Button>
        <nav className="space-y-1">
          <FolderButton
            active={folder === "inbox"}
            icon={InboxIcon}
            label="Inbox"
            onClick={() => setFolder("inbox")}
          />
          <FolderButton
            active={folder === "sent"}
            icon={SendIcon}
            label="Sent"
            onClick={() => setFolder("sent")}
          />
        </nav>
      </div>

      {/* Message list pane / full-screen reader */}
      <div className="flex min-w-0 flex-1 flex-col">
        {selectedThreadId ? (
          <ThreadReader
            email={email}
            threadId={selectedThreadId}
            onClose={() => setSelectedThreadId(null)}
          />
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 md:hidden">
                <Button
                  variant={folder === "inbox" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFolder("inbox")}
                >
                  <InboxIcon className="size-3.5" /> Inbox
                </Button>
                <Button
                  variant={folder === "sent" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFolder("sent")}
                >
                  <SendIcon className="size-3.5" /> Sent
                </Button>
              </div>
              <h2 className="hidden text-lg font-semibold capitalize md:block">{folder}</h2>

              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">
                  {state.messages.length > 0 ? `${rangeStart}–${rangeEnd}` : "0"}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8"
                  disabled={!hasPrev || state.isLoading}
                  onClick={() => loadPage(folder, state.pageIndex - 1)}
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8"
                  disabled={!hasNext || state.isLoading}
                  onClick={() => loadPage(folder, state.pageIndex + 1)}
                >
                  <ChevronRight className="size-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadPage(folder, state.pageIndex)}
                  disabled={state.isLoading}
                >
                  {state.isLoading ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="size-3.5" />
                  )}
                </Button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border">
              {state.isLoading && state.messages.length === 0 && (
                <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Loading your mail…
                </div>
              )}

              {state.errorMessage && (
                <div className="m-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                  {state.errorMessage}
                </div>
              )}

              {!state.isLoading && !state.errorMessage && state.messages.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
                  <InboxIcon className="size-8 opacity-40" />
                  No messages found.
                </div>
              )}

              {threadRows.length > 0 && (
                <div className={cn("divide-y divide-border", state.isLoading && "opacity-60")}>
                  {threadRows.map(({ thread: m, count }) => (
                    <button
                      key={m.thread_id || m.id}
                      onClick={() => setSelectedThreadId(m.thread_id || m.id)}
                      className="flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors hover:bg-accent/50"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate text-sm font-medium">
                          {decodeHtmlEntities(folder === "sent" ? m.to : m.from)}
                          {count > 1 && (
                            <span className="ml-2 text-xs font-normal text-muted-foreground">({count})</span>
                          )}
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">{m.date}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm">{decodeHtmlEntities(m.subject)}</span>
                        {m.has_attachment && <Paperclip className="size-3.5 shrink-0 text-muted-foreground" />}
                      </div>
                      <span className="truncate text-xs text-muted-foreground">{decodeHtmlEntities(m.snippet)}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <ComposeDialog email={email} open={isComposeOpen} onOpenChange={setIsComposeOpen} />
    </div>
  )
}

function ThreadReader({
  email,
  threadId,
  onClose,
}: {
  email: string
  threadId: string
  onClose: () => void
}) {
  const [messages, setMessages] = useState<InboxFullMessage[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  // Only the latest message starts expanded — matches Gmail's own
  // conversation view, since older replies are usually just context.
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    setMessages(null)
    setErrorMessage(null)
    setIsLoading(true)
    inboundService
      .getThread({ thread_id: threadId, email, download_attachments: true })
      .then((res) => {
        if (cancelled) return
        if (res.ok && res.data) {
          setMessages(res.data.messages)
          const last = res.data.messages[res.data.messages.length - 1]
          setExpandedIds(last ? new Set([last.id]) : new Set())
        } else {
          setErrorMessage(res.errorMessage ?? "Failed to load conversation")
        }
        setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [threadId, email])

  function toggleExpanded(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const subject = messages && messages.length > 0 ? messages[messages.length - 1].subject : null

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border">
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <Button variant="ghost" size="icon" className="size-8" onClick={onClose}>
          <ArrowLeft className="size-4" />
        </Button>
        <h2 className="truncate text-base font-semibold">
          {subject ? decodeHtmlEntities(subject) : "Loading…"}
        </h2>
        {messages && messages.length > 1 && (
          <span className="shrink-0 text-xs text-muted-foreground">{messages.length} messages</span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading conversation…
          </div>
        )}

        {errorMessage && !isLoading && (
          <div className="m-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {errorMessage}
          </div>
        )}

        {messages && !isLoading && (
          <div className="mx-auto max-w-3xl space-y-3 p-6">
            {messages.map((message) => {
              const isExpanded = expandedIds.has(message.id)
              return (
                <div key={message.id} className="rounded-lg border border-border">
                  <button
                    onClick={() => toggleExpanded(message.id)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-accent/50"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{decodeHtmlEntities(message.from)}</div>
                      {!isExpanded && (
                        <div className="truncate text-xs text-muted-foreground">
                          {decodeHtmlEntities(message.snippet)}
                        </div>
                      )}
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">{message.date}</span>
                  </button>

                  {isExpanded && (
                    <div className="space-y-3 border-t border-border p-4">
                      <div className="space-y-1 text-sm">
                        <div>
                          <span className="font-medium text-foreground">To:</span>{" "}
                          <span className="text-muted-foreground">{decodeHtmlEntities(message.to)}</span>
                        </div>
                        {message.cc && (
                          <div>
                            <span className="font-medium text-foreground">Cc:</span>{" "}
                            <span className="text-muted-foreground">{decodeHtmlEntities(message.cc)}</span>
                          </div>
                        )}
                      </div>

                      <div className="text-sm leading-relaxed">
                        {message.body_html ? (
                          <div
                            className="[&_a]:text-primary [&_a]:underline [&_img]:max-w-full"
                            dangerouslySetInnerHTML={{ __html: message.body_html }}
                          />
                        ) : (
                          <pre className="whitespace-pre-wrap font-sans">{message.body_text}</pre>
                        )}
                      </div>

                      <AttachmentList attachments={message.attachments} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function ComposeDialog({
  email,
  open,
  onOpenChange,
}: {
  email: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [to, setTo] = useState("")
  const [subject, setSubject] = useState("")
  const [body, setBody] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  function reset() {
    setTo("")
    setSubject("")
    setBody("")
    setErrorMessage(null)
  }

  async function handleSend() {
    setIsSending(true)
    setErrorMessage(null)
    const res = await outboundService.send({ email, to, subject, body })
    setIsSending(false)
    if (res.ok) {
      reset()
      onOpenChange(false)
    } else {
      setErrorMessage(res.errorMessage ?? "Failed to send email")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { onOpenChange(next); if (!next) reset() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New message</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>To</Label>
            <Input value={to} onChange={(e) => setTo(e.target.value)} placeholder="recipient@example.com" />
          </div>
          <div className="space-y-1.5">
            <Label>Subject</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
          </div>
          <div className="space-y-1.5">
            <Label>Message</Label>
            <Textarea rows={8} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write your message…" />
          </div>
          {errorMessage && <p className="text-xs text-destructive">{errorMessage}</p>}
          <div className="flex items-center justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              <X className="size-4" /> Discard
            </Button>
            <Button disabled={isSending || !to || !subject || !body} onClick={handleSend}>
              {isSending ? <Loader2 className="size-4 animate-spin" /> : <SendIcon className="size-4" />}
              Send
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

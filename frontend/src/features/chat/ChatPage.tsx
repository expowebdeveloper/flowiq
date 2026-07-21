import { useEffect, useMemo, useRef, useState } from "react"
import { Loader2, Send as SendIcon, Users } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { useAuth } from "@/contexts/AuthContext"
import { useChatSocket } from "@/hooks/useChatSocket"
import { chatService } from "@/services/chatService"
import type { ChatMessage, ChatUser } from "@/types/api"

function initialsFor(email: string): string {
  return email.slice(0, 2).toUpperCase()
}

export function ChatPage() {
  const { user, token } = useAuth()
  const [users, setUsers] = useState<ChatUser[]>([])
  const [selectedUser, setSelectedUser] = useState<ChatUser | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [isLoadingUsers, setIsLoadingUsers] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const scrollBottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setIsLoadingUsers(true)
    chatService.listUsers().then((result) => {
      if (result.ok && result.data) setUsers(result.data)
      setIsLoadingUsers(false)
    })
  }, [])

  useEffect(() => {
    if (!selectedUser) return
    setIsLoadingMessages(true)
    chatService.getConversation(selectedUser.id).then((result) => {
      if (result.ok && result.data) setMessages(result.data)
      setIsLoadingMessages(false)
    })
  }, [selectedUser])

  useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const { sendMessage } = useChatSocket(token, (incoming) => {
    setMessages((prev) => {
      const belongsToOpenConversation =
        selectedUser &&
        (incoming.sender_id === selectedUser.id || incoming.recipient_id === selectedUser.id)
      return belongsToOpenConversation ? [...prev, incoming] : prev
    })
  })

  const handleSend = () => {
    const body = draft.trim()
    if (!body || !selectedUser) return
    sendMessage(selectedUser.id, body)
    setDraft("")
  }

  const currentUserId = user?.id ?? null

  const sortedUsers = useMemo(
    () => [...users].sort((a, b) => a.email.localeCompare(b.email)),
    [users],
  )

  return (
    <div className="flex h-[calc(100vh_-_3.5rem)]">
      <aside className="w-72 shrink-0 border-r border-border">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Users className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium">Users</span>
        </div>
        <ScrollArea className="h-[calc(100%_-_3rem)]">
          {isLoadingUsers ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            </div>
          ) : sortedUsers.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground">No other users yet.</p>
          ) : (
            <ul>
              {sortedUsers.map((u) => (
                <li key={u.id}>
                  <button
                    onClick={() => setSelectedUser(u)}
                    className={cn(
                      "flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:bg-accent",
                      selectedUser?.id === u.id && "bg-accent",
                    )}
                  >
                    <Avatar className="size-8">
                      <AvatarFallback className="text-xs">{initialsFor(u.email)}</AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{u.email}</p>
                      <p className="text-xs text-muted-foreground">{u.role}</p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </ScrollArea>
      </aside>

      <section className="flex flex-1 flex-col">
        {!selectedUser ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Select a user to start chatting.
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b border-border px-4 py-3">
              <Avatar className="size-8">
                <AvatarFallback className="text-xs">{initialsFor(selectedUser.email)}</AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium">{selectedUser.email}</span>
            </div>

            <ScrollArea className="flex-1 px-4 py-4">
              {isLoadingMessages ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {messages.map((m) => {
                    const isMine = m.sender_id === currentUserId
                    return (
                      <div
                        key={m.id}
                        className={cn("flex", isMine ? "justify-end" : "justify-start")}
                      >
                        <div
                          className={cn(
                            "max-w-[70%] rounded-lg px-3 py-2 text-sm",
                            isMine
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-foreground",
                          )}
                        >
                          <p className="whitespace-pre-wrap break-words">{m.body}</p>
                          <p
                            className={cn(
                              "mt-1 text-[10px] opacity-70",
                              isMine ? "text-primary-foreground" : "text-muted-foreground",
                            )}
                          >
                            {new Date(m.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                  <div ref={scrollBottomRef} />
                </div>
              )}
            </ScrollArea>

            <div className="flex items-center gap-2 border-t border-border p-3">
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSend()
                }}
                placeholder="Type a message..."
              />
              <Button onClick={handleSend} disabled={!draft.trim()} size="icon">
                <SendIcon className="size-4" />
              </Button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

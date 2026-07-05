import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useAccounts } from "../hooks/useAccounts"
import { useAccountLiveSocket } from "../hooks/useAccountLiveSocket"
import { getDialogs, getMessages, sendMessage } from "../api/chat"
import { DialogList } from "../components/chat/DialogList"
import { MessageThread } from "../components/chat/MessageThread"
import { MessageComposer } from "../components/chat/MessageComposer"

export function ChatPage() {
  const { data: accounts } = useAccounts()
  const [accountId, setAccountId] = useState<string | null>(null)
  const [selectedPeerId, setSelectedPeerId] = useState<number | null>(null)
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!accountId && accounts && accounts.length > 0) {
      setAccountId(accounts[0].id)
    }
  }, [accounts, accountId])

  useAccountLiveSocket(accountId)

  const dialogsQuery = useQuery({
    queryKey: ["dialogs", accountId],
    queryFn: () => getDialogs(accountId as string),
    enabled: !!accountId,
  })

  const messagesQuery = useQuery({
    queryKey: ["messages", accountId, selectedPeerId],
    queryFn: () => getMessages(accountId as string, selectedPeerId as number),
    enabled: !!accountId && selectedPeerId !== null,
  })

  const sendMutation = useMutation({
    mutationFn: (text: string) => sendMessage(accountId as string, selectedPeerId as number, text),
    onSuccess: (message) => {
      queryClient.setQueryData(["messages", accountId, selectedPeerId], (old: typeof message[] | undefined) =>
        old ? [...old, message] : [message]
      )
      queryClient.invalidateQueries({ queryKey: ["dialogs", accountId] })
    },
  })

  if (!accounts || accounts.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
        먼저 계정 페이지에서 텔레그램 계정을 로그인하세요.
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2">
        <span className="text-sm text-muted-foreground">계정</span>
        <select
          className="rounded-md border border-border bg-card px-2 py-1 text-sm"
          value={accountId ?? ""}
          onChange={(e) => {
            setAccountId(e.target.value)
            setSelectedPeerId(null)
          }}
        >
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-72 shrink-0 overflow-y-auto border-r border-border">
          {dialogsQuery.isLoading && <p className="p-4 text-sm text-muted-foreground">불러오는 중...</p>}
          {dialogsQuery.data && (
            <DialogList
              dialogs={dialogsQuery.data}
              selectedPeerId={selectedPeerId}
              onSelect={setSelectedPeerId}
            />
          )}
        </div>

        <div className="flex flex-1 flex-col">
          {selectedPeerId === null ? (
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
              왼쪽에서 대화를 선택하세요.
            </div>
          ) : (
            <>
              {messagesQuery.isLoading ? (
                <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                  불러오는 중...
                </div>
              ) : (
                <MessageThread messages={messagesQuery.data ?? []} />
              )}
              <MessageComposer onSend={(text) => sendMutation.mutate(text)} disabled={sendMutation.isPending} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}

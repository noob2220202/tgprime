import { useEffect } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { liveSocketUrl, type Message } from "../api/chat"

interface NewMessageEvent {
  type: "new_message"
  peer_id: number
  message: Message
}

export function useAccountLiveSocket(accountId: string | null) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!accountId) return

    const ws = new WebSocket(liveSocketUrl(accountId))

    ws.onmessage = (event) => {
      let data: NewMessageEvent
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      if (data.type !== "new_message") return

      queryClient.setQueryData<Message[]>(["messages", accountId, data.peer_id], (old) => {
        if (!old) return old
        if (old.some((m) => m.id === data.message.id)) return old
        return [...old, data.message]
      })

      queryClient.invalidateQueries({ queryKey: ["dialogs", accountId] })
    }

    return () => {
      ws.close()
    }
  }, [accountId, queryClient])
}

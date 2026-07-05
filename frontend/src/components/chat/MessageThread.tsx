import { cn } from "../../lib/utils"
import type { Message } from "../../api/chat"

export function MessageThread({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">메시지가 없습니다.</div>
  }

  return (
    <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
      {messages.map((m) => (
        <div
          key={m.id}
          className={cn(
            "max-w-[70%] rounded-lg px-3 py-2 text-sm",
            m.out ? "self-end bg-primary text-primary-foreground" : "self-start bg-muted text-foreground"
          )}
        >
          <p className="whitespace-pre-wrap break-words">{m.text || <em className="opacity-60">(미디어 메시지)</em>}</p>
          <p className={cn("mt-1 text-[10px] opacity-70", m.out ? "text-right" : "text-left")}>
            {new Date(m.date).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  )
}

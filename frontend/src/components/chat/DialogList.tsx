import { cn } from "../../lib/utils"
import type { Dialog } from "../../api/chat"

export function DialogList({
  dialogs,
  selectedPeerId,
  onSelect,
}: {
  dialogs: Dialog[]
  selectedPeerId: number | null
  onSelect: (peerId: number) => void
}) {
  if (dialogs.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">대화가 없습니다.</p>
  }

  return (
    <ul className="divide-y divide-border overflow-y-auto">
      {dialogs.map((d) => (
        <li key={d.peer_id}>
          <button
            onClick={() => onSelect(d.peer_id)}
            className={cn(
              "flex w-full flex-col items-start gap-0.5 px-4 py-3 text-left hover:bg-muted",
              selectedPeerId === d.peer_id && "bg-muted"
            )}
          >
            <div className="flex w-full items-center justify-between">
              <span className="truncate text-sm font-medium">{d.title}</span>
              {d.unread_count > 0 && (
                <span className="ml-2 shrink-0 rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                  {d.unread_count}
                </span>
              )}
            </div>
            {d.last_message_text && (
              <span className="w-full truncate text-xs text-muted-foreground">{d.last_message_text}</span>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}

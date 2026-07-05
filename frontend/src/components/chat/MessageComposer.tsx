import { useState } from "react"
import { Send } from "lucide-react"
import { Input } from "../ui/input"
import { Button } from "../ui/button"

export function MessageComposer({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState("")

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText("")
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-border p-3">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="메시지 입력..."
        disabled={disabled}
      />
      <Button type="submit" size="sm" disabled={disabled || !text.trim()}>
        <Send size={16} />
      </Button>
    </form>
  )
}

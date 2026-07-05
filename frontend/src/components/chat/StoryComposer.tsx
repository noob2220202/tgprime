import { useRef, useState } from "react"
import { Modal } from "../ui/modal"
import { Input } from "../ui/input"
import { Button } from "../ui/button"
import { postStory } from "../../api/stories"
import { ApiError } from "../../api/client"

export function StoryComposer({
  open,
  onClose,
  accountId,
}: {
  open: boolean
  onClose: () => void
  accountId: string
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [caption, setCaption] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function handleClose() {
    setCaption("")
    setError(null)
    onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setError("사진을 선택하세요.")
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await postStory(accountId, file, caption || undefined)
      handleClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "스토리 업로드 중 오류가 발생했습니다.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} onClose={handleClose} title="스토리 업로드">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          required
          className="rounded-md border border-border bg-card px-3 py-2 text-sm"
        />
        <Input placeholder="캡션 (선택)" value={caption} onChange={(e) => setCaption(e.target.value)} />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "업로드 중..." : "게시"}
        </Button>
      </form>
    </Modal>
  )
}

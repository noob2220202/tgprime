import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useAccounts } from "../hooks/useAccounts"
import { getAutoReply, updateAutoReply } from "../api/autoReply"
import { Card, CardContent, CardHeader } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"

export function AutoReplySettingsPage() {
  const { data: accounts } = useAccounts()
  const [accountId, setAccountId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const [enabled, setEnabled] = useState(false)
  const [replyText, setReplyText] = useState("")
  const [cooldownMinutes, setCooldownMinutes] = useState(60)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!accountId && accounts && accounts.length > 0) {
      setAccountId(accounts[0].id)
    }
  }, [accounts, accountId])

  const ruleQuery = useQuery({
    queryKey: ["auto-reply", accountId],
    queryFn: () => getAutoReply(accountId as string),
    enabled: !!accountId,
  })

  useEffect(() => {
    if (ruleQuery.data) {
      setEnabled(ruleQuery.data.enabled)
      setReplyText(ruleQuery.data.reply_text)
      setCooldownMinutes(ruleQuery.data.cooldown_minutes)
    }
  }, [ruleQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAutoReply(accountId as string, { enabled, reply_text: replyText, cooldown_minutes: cooldownMinutes }),
    onSuccess: (rule) => {
      queryClient.setQueryData(["auto-reply", accountId], rule)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
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
    <div className="p-6">
      <h1 className="mb-4 text-lg font-semibold">자동응답</h1>
      <Card className="max-w-xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">계정</span>
            <select
              className="rounded-md border border-border bg-card px-2 py-1 text-sm"
              value={accountId ?? ""}
              onChange={(e) => setAccountId(e.target.value)}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {ruleQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">불러오는 중...</p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                saveMutation.mutate()
              }}
              className="flex flex-col gap-4"
            >
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
                1:1 대화에 자동으로 응답합니다 (부재중 응답)
              </label>

              <div>
                <p className="mb-1 text-sm font-medium">응답 문구</p>
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="예: 지금은 답장이 어렵습니다. 곧 연락드리겠습니다."
                />
              </div>

              <div>
                <p className="mb-1 text-sm font-medium">동일 상대 재응답 쿨다운 (분)</p>
                <Input
                  type="number"
                  min={1}
                  value={cooldownMinutes}
                  onChange={(e) => setCooldownMinutes(Number(e.target.value))}
                  className="max-w-[120px]"
                />
              </div>

              <div className="flex items-center gap-3">
                <Button type="submit" disabled={saveMutation.isPending}>
                  {saveMutation.isPending ? "저장 중..." : "저장"}
                </Button>
                {saved && <span className="text-sm text-success">저장됨</span>}
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

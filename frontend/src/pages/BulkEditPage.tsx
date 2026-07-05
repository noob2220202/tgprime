import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useAccounts } from "../hooks/useAccounts"
import { useJob } from "../hooks/useJobs"
import { createJob } from "../api/jobs"
import { ApiError } from "../api/client"
import { Card, CardContent, CardHeader } from "../components/ui/card"
import { Input } from "../components/ui/input"
import { Button } from "../components/ui/button"
import { JobItemStatusBadge, JobStatusBadge } from "../components/ui/badge"

export function BulkEditPage() {
  const { data: accounts } = useAccounts()
  const queryClient = useQueryClient()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [bio, setBio] = useState("")
  const [username, setUsername] = useState("")
  const [photo, setPhoto] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)

  const jobQuery = useJob(activeJobId)

  const createMutation = useMutation({
    mutationFn: () =>
      createJob(
        {
          account_ids: [...selected],
          first_name: firstName || undefined,
          last_name: lastName || undefined,
          bio: bio || undefined,
          username: username || undefined,
        },
        photo
      ),
    onSuccess: (job) => {
      setActiveJobId(job.id)
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  function toggle(accountId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(accountId)) next.delete(accountId)
      else next.add(accountId)
      return next
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (selected.size === 0) {
      setError("대상 계정을 하나 이상 선택하세요.")
      return
    }
    if (!firstName && !lastName && !bio && !username && !photo) {
      setError("변경할 항목을 하나 이상 입력하세요.")
      return
    }
    try {
      await createMutation.mutateAsync()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "작업 생성 중 오류가 발생했습니다.")
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">일괄 편집</h1>
          <p className="text-sm text-muted-foreground">선택한 계정에 동일한 프로필 정보를 적용합니다.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <p className="mb-2 text-sm font-medium">대상 계정 ({selected.size}개 선택)</p>
              <div className="max-h-40 overflow-y-auto rounded-md border border-border">
                {accounts?.map((a) => (
                  <label key={a.id} className="flex items-center gap-2 border-b border-border px-3 py-2 text-sm last:border-0">
                    <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggle(a.id)} />
                    {a.label}
                  </label>
                ))}
                {!accounts?.length && (
                  <p className="px-3 py-2 text-sm text-muted-foreground">등록된 계정이 없습니다.</p>
                )}
              </div>
            </div>

            <Input placeholder="이름 (선택)" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <Input placeholder="성 (선택)" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            <Input placeholder="소개(bio) (선택)" value={bio} onChange={(e) => setBio(e.target.value)} />
            <Input placeholder="유저네임 (선택)" value={username} onChange={(e) => setUsername(e.target.value)} />
            <div>
              <p className="mb-1 text-sm font-medium">프로필 사진 (선택, 전체 대상 동일 사진)</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
                className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
              />
            </div>

            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "생성 중..." : "일괄 작업 시작"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">진행 상황</h2>
        </CardHeader>
        <CardContent>
          {!jobQuery.data && <p className="text-sm text-muted-foreground">작업을 시작하면 여기에 진행 상황이 표시됩니다.</p>}
          {jobQuery.data && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <JobStatusBadge status={jobQuery.data.status} />
                <span className="text-sm text-muted-foreground">
                  {jobQuery.data.succeeded_count + jobQuery.data.failed_count} / {jobQuery.data.total_items} 처리됨
                  (성공 {jobQuery.data.succeeded_count}, 실패 {jobQuery.data.failed_count})
                </span>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-muted-foreground">
                  <tr>
                    <th className="py-2 font-medium">계정 ID</th>
                    <th className="py-2 font-medium">상태</th>
                    <th className="py-2 font-medium">비고</th>
                  </tr>
                </thead>
                <tbody>
                  {jobQuery.data.items.map((item) => (
                    <tr key={item.id} className="border-b border-border last:border-0">
                      <td className="py-2 text-muted-foreground">{item.account_id.slice(0, 8)}</td>
                      <td className="py-2">
                        <JobItemStatusBadge status={item.status} />
                      </td>
                      <td className="py-2 text-muted-foreground">{item.error_message ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

import { useState } from "react"
import { Card, CardContent } from "../components/ui/card"
import { JobItemStatusBadge, JobStatusBadge } from "../components/ui/badge"
import { useJob, useJobs } from "../hooks/useJobs"

export function JobsHistoryPage() {
  const { data: jobs, isLoading } = useJobs()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const detailQuery = useJob(expandedId)

  return (
    <div className="p-6">
      <h1 className="mb-4 text-lg font-semibold">작업 이력</h1>

      {isLoading && <p className="text-sm text-muted-foreground">불러오는 중...</p>}
      {!isLoading && jobs?.length === 0 && (
        <Card className="p-8 text-center text-sm text-muted-foreground">아직 실행한 일괄 작업이 없습니다.</Card>
      )}

      <div className="flex flex-col gap-3">
        {jobs?.map((job) => (
          <Card key={job.id}>
            <button
              className="flex w-full items-center justify-between px-4 py-3 text-left"
              onClick={() => setExpandedId(expandedId === job.id ? null : job.id)}
            >
              <div className="flex items-center gap-3">
                <JobStatusBadge status={job.status} />
                <span className="text-sm">{new Date(job.created_at).toLocaleString()}</span>
              </div>
              <span className="text-sm text-muted-foreground">
                성공 {job.succeeded_count} / 실패 {job.failed_count} / 전체 {job.total_items}
              </span>
            </button>
            {expandedId === job.id && (
              <CardContent className="border-t border-border">
                {detailQuery.isLoading ? (
                  <p className="text-sm text-muted-foreground">불러오는 중...</p>
                ) : (
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-muted-foreground">
                      <tr>
                        <th className="py-2 font-medium">계정 ID</th>
                        <th className="py-2 font-medium">상태</th>
                        <th className="py-2 font-medium">시도 횟수</th>
                        <th className="py-2 font-medium">비고</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detailQuery.data?.items.map((item) => (
                        <tr key={item.id} className="border-b border-border last:border-0">
                          <td className="py-2 text-muted-foreground">{item.account_id.slice(0, 8)}</td>
                          <td className="py-2">
                            <JobItemStatusBadge status={item.status} />
                          </td>
                          <td className="py-2 text-muted-foreground">{item.attempt_count}</td>
                          <td className="py-2 text-muted-foreground">{item.error_message ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}

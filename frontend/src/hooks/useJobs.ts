import { useQuery } from "@tanstack/react-query"
import { getJob, listJobs } from "../api/jobs"

const ACTIVE_STATUSES = new Set(["pending", "running"])

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data
      return jobs?.some((j) => ACTIVE_STATUSES.has(j.status)) ? 2000 : false
    },
  })
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => (ACTIVE_STATUSES.has(query.state.data?.status ?? "") ? 1500 : false),
  })
}

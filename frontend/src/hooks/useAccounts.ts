import { useQuery } from "@tanstack/react-query"
import { listAccounts } from "../api/accounts"

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  })
}

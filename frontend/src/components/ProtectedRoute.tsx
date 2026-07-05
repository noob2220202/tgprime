import { Navigate } from "react-router-dom"
import { useCurrentUser } from "../hooks/useAuth"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading, isError } = useCurrentUser()

  if (isLoading) {
    return <div className="flex min-h-svh items-center justify-center text-muted-foreground">로딩 중...</div>
  }
  if (isError || !user) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card, CardContent, CardHeader } from "../components/ui/card"
import { useLogin } from "../hooks/useAuth"
import { ApiError } from "../api/client"

export function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const loginMutation = useLogin()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await loginMutation.mutateAsync({ username, password })
      navigate("/accounts")
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("아이디 또는 비밀번호가 올바르지 않습니다.")
      } else if (err instanceof ApiError && err.status === 429) {
        setError("로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.")
      } else {
        setError("로그인 중 오류가 발생했습니다.")
      }
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <h1 className="text-lg font-semibold">Telegram Prime</h1>
          <p className="text-sm text-muted-foreground">관리자 계정으로 로그인하세요</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <Input
              placeholder="아이디"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
            />
            <Input
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={loginMutation.isPending} className="mt-1">
              {loginMutation.isPending ? "로그인 중..." : "로그인"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

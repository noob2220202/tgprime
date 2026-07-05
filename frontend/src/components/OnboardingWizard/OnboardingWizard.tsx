import { useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Modal } from "../ui/modal"
import { Input } from "../ui/input"
import { Button } from "../ui/button"
import { loginStart, loginVerify2fa, loginVerifyCode } from "../../api/accounts"
import { ApiError } from "../../api/client"

type Step = "phone" | "code" | "2fa"

export function OnboardingWizard({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()

  const [step, setStep] = useState<Step>("phone")
  const [label, setLabel] = useState("")
  const [phoneNumber, setPhoneNumber] = useState("")
  const [apiId, setApiId] = useState("")
  const [apiHash, setApiHash] = useState("")
  const [code, setCode] = useState("")
  const [password, setPassword] = useState("")
  const [loginSessionId, setLoginSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function reset() {
    setStep("phone")
    setLabel("")
    setPhoneNumber("")
    setApiId("")
    setApiHash("")
    setCode("")
    setPassword("")
    setLoginSessionId(null)
    setError(null)
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handlePhoneSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const res = await loginStart({
        label: label || phoneNumber,
        phone_number: phoneNumber,
        api_id: Number(apiId),
        api_hash: apiHash,
      })
      setLoginSessionId(res.login_session_id)
      setStep("code")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인 시작 중 오류가 발생했습니다.")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCodeSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!loginSessionId) return
    setError(null)
    setSubmitting(true)
    try {
      const res = await loginVerifyCode({ login_session_id: loginSessionId, code })
      if (res.status === "needs_2fa") {
        setStep("2fa")
      } else {
        await queryClient.invalidateQueries({ queryKey: ["accounts"] })
        handleClose()
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "코드 확인 중 오류가 발생했습니다.")
    } finally {
      setSubmitting(false)
    }
  }

  async function handle2faSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!loginSessionId) return
    setError(null)
    setSubmitting(true)
    try {
      await loginVerify2fa({ login_session_id: loginSessionId, password })
      await queryClient.invalidateQueries({ queryKey: ["accounts"] })
      handleClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "2단계 인증 중 오류가 발생했습니다.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} onClose={handleClose} title="텔레그램 계정 로그인">
      {step === "phone" && (
        <form onSubmit={handlePhoneSubmit} className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            my.telegram.org에서 발급받은 api_id / api_hash가 필요합니다.
          </p>
          <Input placeholder="계정 별칭 (예: 영업1팀)" value={label} onChange={(e) => setLabel(e.target.value)} />
          <Input
            placeholder="전화번호 (+82...)"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            required
          />
          <Input placeholder="api_id" value={apiId} onChange={(e) => setApiId(e.target.value)} required />
          <Input placeholder="api_hash" value={apiHash} onChange={(e) => setApiHash(e.target.value)} required />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "코드 요청 중..." : "인증 코드 받기"}
          </Button>
        </form>
      )}

      {step === "code" && (
        <form onSubmit={handleCodeSubmit} className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">텔레그램 앱으로 전송된 인증 코드를 입력하세요.</p>
          <Input
            placeholder="인증 코드"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoFocus
            required
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "확인 중..." : "확인"}
          </Button>
        </form>
      )}

      {step === "2fa" && (
        <form onSubmit={handle2faSubmit} className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">2단계 인증 비밀번호를 입력하세요.</p>
          <Input
            type="password"
            placeholder="2단계 인증 비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            required
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? "확인 중..." : "로그인 완료"}
          </Button>
        </form>
      )}
    </Modal>
  )
}

import { cn } from "../../lib/utils"

export type BadgeTone = "success" | "warning" | "danger" | "info" | "neutral"

const toneClasses: Record<BadgeTone, string> = {
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  danger: "bg-danger-bg text-danger",
  info: "bg-info-bg text-info",
  neutral: "bg-muted text-muted-foreground",
}

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone]
      )}
    >
      {children}
    </span>
  )
}

const ACCOUNT_STATUS_TONE: Record<string, BadgeTone> = {
  active: "success",
  pending_login: "neutral",
  needs_2fa: "warning",
  flood_wait: "warning",
  banned: "danger",
  frozen: "danger",
  error: "danger",
  disconnected: "neutral",
}

const ACCOUNT_STATUS_LABEL: Record<string, string> = {
  active: "활성",
  pending_login: "로그인 대기",
  needs_2fa: "2FA 필요",
  flood_wait: "FloodWait",
  banned: "차단됨",
  frozen: "동결됨",
  error: "오류",
  disconnected: "연결 끊김",
}

export function AccountStatusBadge({ status }: { status: string }) {
  return (
    <Badge tone={ACCOUNT_STATUS_TONE[status] ?? "neutral"}>
      {ACCOUNT_STATUS_LABEL[status] ?? status}
    </Badge>
  )
}

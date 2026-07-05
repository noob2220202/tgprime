import { useState } from "react"
import { Plus } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card } from "../components/ui/card"
import { AccountStatusBadge } from "../components/ui/badge"
import { OnboardingWizard } from "../components/OnboardingWizard/OnboardingWizard"
import { useAccounts } from "../hooks/useAccounts"

export function AccountsPage() {
  const [wizardOpen, setWizardOpen] = useState(false)
  const { data: accounts, isLoading } = useAccounts()

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">계정</h1>
        <Button size="sm" onClick={() => setWizardOpen(true)}>
          <Plus size={16} />
          계정 추가
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">불러오는 중...</p>}

      {!isLoading && accounts?.length === 0 && (
        <Card className="p-8 text-center text-sm text-muted-foreground">
          아직 등록된 계정이 없습니다. "계정 추가"로 텔레그램 계정을 로그인하세요.
        </Card>
      )}

      {!!accounts?.length && (
        <Card>
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">별칭</th>
                <th className="px-4 py-3 font-medium">전화번호</th>
                <th className="px-4 py-3 font-medium">유저네임</th>
                <th className="px-4 py-3 font-medium">이름</th>
                <th className="px-4 py-3 font-medium">상태</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">{account.label}</td>
                  <td className="px-4 py-3 text-muted-foreground">{account.phone_number}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {account.username ? `@${account.username}` : "-"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {[account.first_name, account.last_name].filter(Boolean).join(" ") || "-"}
                  </td>
                  <td className="px-4 py-3">
                    <AccountStatusBadge status={account.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <OnboardingWizard open={wizardOpen} onClose={() => setWizardOpen(false)} />
    </div>
  )
}

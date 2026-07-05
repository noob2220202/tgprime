import { Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { LoginPage } from "./pages/LoginPage"
import { AccountsPage } from "./pages/AccountsPage"
import { ChatPage } from "./pages/ChatPage"
import { PlaceholderPage } from "./pages/PlaceholderPage"

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/bulk-edit" element={<PlaceholderPage title="일괄 편집" />} />
        <Route path="/auto-reply" element={<PlaceholderPage title="자동응답" />} />
        <Route path="/jobs" element={<PlaceholderPage title="작업 이력" />} />
        <Route path="/" element={<Navigate to="/accounts" replace />} />
      </Route>
    </Routes>
  )
}

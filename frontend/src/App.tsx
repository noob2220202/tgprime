import { Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { LoginPage } from "./pages/LoginPage"
import { AccountsPage } from "./pages/AccountsPage"
import { ChatPage } from "./pages/ChatPage"
import { BulkEditPage } from "./pages/BulkEditPage"
import { JobsHistoryPage } from "./pages/JobsHistoryPage"
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
        <Route path="/bulk-edit" element={<BulkEditPage />} />
        <Route path="/auto-reply" element={<PlaceholderPage title="자동응답" />} />
        <Route path="/jobs" element={<JobsHistoryPage />} />
        <Route path="/" element={<Navigate to="/accounts" replace />} />
      </Route>
    </Routes>
  )
}

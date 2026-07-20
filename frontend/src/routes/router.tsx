import { createBrowserRouter } from "react-router-dom"
import { AppLayout } from "@/components/layout/AppLayout"
import { LoginPage } from "@/pages/LoginPage"
import { RoleHome } from "@/pages/RoleHome"
import { MailPage } from "@/features/mail/MailPage"
import { ChatPage } from "@/features/chat/ChatPage"
import { LoansPage } from "@/features/loans/LoansPage"
import { BanksPage } from "@/features/banks/BanksPage"
import { AttachmentsPage } from "@/features/attachments/AttachmentsPage"
import { SettingsPage } from "@/features/settings/SettingsPage"
import { KycFormPage } from "@/features/kyc/KycFormPage"
import { JsonVerifyPage } from "@/features/json-verify/JsonVerifyPage"
import { LoanApplyPage } from "@/features/loan-apply/LoanApplyPage"
import { LeadsPage } from "@/features/leads/LeadsPage"
import { BankNotificationsPage } from "@/features/bank-notifications/BankNotificationsPage"
import { AiActivityPage } from "@/features/ai-activity/AiActivityPage"
import { ProtectedRoute } from "./ProtectedRoute"

export const router = createBrowserRouter([
  { path: "/", element: <RoleHome /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/kyc/:token", element: <KycFormPage /> },
  { path: "/loan-apply", element: <LoanApplyPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/notifications", element: <BankNotificationsPage /> },
          { path: "/mail", element: <MailPage /> },
          { path: "/chat", element: <ChatPage /> },
          { path: "/loans", element: <LoansPage /> },
          { path: "/banks", element: <BanksPage /> },
          { path: "/attachments", element: <AttachmentsPage /> },
          { path: "/verify-json", element: <JsonVerifyPage /> },
          { path: "/leads", element: <LeadsPage /> },
          { path: "/ai-activity", element: <AiActivityPage /> },
          { path: "/settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
])


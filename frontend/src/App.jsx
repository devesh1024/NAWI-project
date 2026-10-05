import React from "react";
import { Routes, Route, Outlet } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { CustomCursor } from "@/components/cursor/CustomCursor";
import AppShell from "@/components/layout/AppShell";
import { ChatProvider } from "@/hooks/useChat";
import { RouteGuard } from "@/components/layout/RouteGuard";
import { ToastStack } from "@/components/chat/ToastStack";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Verify from "@/pages/Verify";
import Dashboard from "@/pages/Dashboard";
import Instruments from "@/pages/Instruments";
import TestSessions from "@/pages/TestSessions";
import TestSessionDetail from "@/pages/TestSessionDetail";
import Reports from "@/pages/Reports";
import Equipment from "@/pages/Equipment";
import Standards from "@/pages/Standards";
import Users from "@/pages/Users";
import AuditLog from "@/pages/AuditLog";
import Settings from "@/pages/Settings";
import TeamDesk from "@/pages/TeamDesk";

export default function App() {
  return (
    <AuthProvider>
      <CustomCursor />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        {/* Public, no auth: anyone with a report (account or not) can check it */}
        <Route path="/verify" element={<Verify />} />
        <Route path="/verify/:testSessionId" element={<Verify />} />

        {/* Everything signed-in shares one chat connection, so notifications keep
            arriving while you move between the app and TeamDesk. */}
        <Route
          element={
            <ProtectedRoute>
              <ChatProvider>
                <Outlet />
                <ToastStack />
              </ChatProvider>
            </ProtectedRoute>
          }
        >
          <Route path="/app" element={<AppShell />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="instruments" element={<RouteGuard page="instruments"><Instruments /></RouteGuard>} />
            <Route path="test-sessions" element={<RouteGuard page="test-sessions"><TestSessions /></RouteGuard>} />
            <Route path="test-sessions/:id" element={<RouteGuard page="test-sessions"><TestSessionDetail /></RouteGuard>} />
            <Route path="reports" element={<RouteGuard page="reports"><Reports /></RouteGuard>} />
            <Route path="equipment" element={<RouteGuard page="equipment"><Equipment /></RouteGuard>} />
            <Route path="standards" element={<RouteGuard page="standards"><Standards /></RouteGuard>} />
            <Route path="users" element={<RouteGuard page="users"><Users /></RouteGuard>} />
            <Route path="audit-log" element={<RouteGuard page="audit-log"><AuditLog /></RouteGuard>} />
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route path="/app/teamdesk" element={<TeamDesk />} />
          <Route path="/app/teamdesk/:conversationId" element={<TeamDesk />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

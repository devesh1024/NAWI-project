import React from "react";
import { Routes, Route, Outlet } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { CustomCursor } from "@/components/cursor/CustomCursor";
import AppShell from "@/components/layout/AppShell";
import { ChatProvider } from "@/hooks/useChat";
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
            <Route path="instruments" element={<Instruments />} />
            <Route path="test-sessions" element={<TestSessions />} />
            <Route path="test-sessions/:id" element={<TestSessionDetail />} />
            <Route path="reports" element={<Reports />} />
            <Route path="equipment" element={<Equipment />} />
            <Route path="standards" element={<Standards />} />
            <Route path="users" element={<Users />} />
            <Route path="audit-log" element={<AuditLog />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route path="/app/teamdesk" element={<TeamDesk />} />
          <Route path="/app/teamdesk/:conversationId" element={<TeamDesk />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ContentLibraryPage } from "./pages/ContentLibraryPage";
import { AIStudioPage } from "./pages/AIStudioPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { CommentsPage } from "./pages/CommentsPage";
import { SEOPage } from "./pages/SEOPage";
import { CalendarPage } from "./pages/CalendarPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { StrategyPage } from "./pages/StrategyPage";
import { AgentsPage } from "./pages/AgentsPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { getMe, login, register } from "./services/api";
import type { AuthUser } from "./types/api";
import type { AppRoute } from "./types/routes";

const STORAGE_KEY = "aism_access_token";

const ROUTE_LABELS: Record<AppRoute, string> = {
  dashboard: "Dashboard",
  content: "Content",
  "ai-studio": "AI Studio",
  calendar: "Calendar",
  seo: "SEO",
  comments: "Comments",
  analytics: "Analytics",
  strategy: "Strategy",
  knowledge: "Knowledge",
  agents: "Agents",
  approvals: "Approvals",
  settings: "Settings",
};

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [route, setRoute] = useState<AppRoute>("dashboard");
  const [isCheckingSession, setIsCheckingSession] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;
    setIsCheckingSession(true);
    getMe(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
      })
      .finally(() => setIsCheckingSession(false));
  }, [token]);

  const content = useMemo(() => {
    if (!token) return null;
    if (route === "dashboard") return <DashboardPage token={token} />;
    if (route === "content") return <ContentLibraryPage token={token} />;
    if (route === "ai-studio") return <AIStudioPage token={token} />;
    if (route === "calendar") return <CalendarPage token={token} />;
    if (route === "seo") return <SEOPage token={token} />;
    if (route === "comments") return <CommentsPage token={token} />;
    if (route === "analytics") return <AnalyticsPage token={token} />;
    if (route === "settings") return <SettingsPage token={token} />;
    if (route === "knowledge") return <KnowledgeBasePage token={token} />;
    if (route === "strategy") return <StrategyPage token={token} />;
    if (route === "agents") return <AgentsPage token={token} />;
    if (route === "approvals") return <ApprovalsPage token={token} />;
    return <PlaceholderPage title={ROUTE_LABELS[route]} />;
  }, [route, token]);

  async function handleLogin(email: string, password: string) {
    const response = await login(email, password);
    localStorage.setItem(STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setUser(await getMe(response.access_token));
  }

  async function handleRegister(email: string, password: string, fullName: string) {
    await register(email, password, fullName);
    await handleLogin(email, password);
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    setRoute("dashboard");
  }

  if (isCheckingSession) {
    return <main className="flex min-h-screen items-center justify-center bg-slate-100 text-sm text-slate-600">Loading session...</main>;
  }

  if (!token || !user) {
    return <LoginPage onLogin={handleLogin} onRegister={handleRegister} />;
  }

  return (
    <AppShell currentRoute={route} onRouteChange={setRoute} onLogout={handleLogout} user={user}>
      {content}
    </AppShell>
  );
}

export default App;

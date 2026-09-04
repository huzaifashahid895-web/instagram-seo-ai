import type { AuthUser } from "../types/api";
import type { AppRoute } from "../types/routes";

type AppShellProps = {
  children: React.ReactNode;
  currentRoute: AppRoute;
  onRouteChange: (route: AppRoute) => void;
  onLogout: () => void;
  user: AuthUser;
};

const NAV_ITEMS: Array<{ route: AppRoute; label: string }> = [
  { route: "dashboard", label: "Dashboard" },
  { route: "content", label: "Content" },
  { route: "ai-studio", label: "AI Studio" },
  { route: "calendar", label: "Calendar" },
  { route: "seo", label: "SEO" },
  { route: "comments", label: "Comments" },
  { route: "analytics", label: "Analytics" },
  { route: "strategy", label: "Strategy" },
  { route: "knowledge", label: "Knowledge" },
  { route: "agents", label: "Agents" },
  { route: "approvals", label: "Approvals" },
  { route: "settings", label: "Settings" },
];

export function AppShell({ children, currentRoute, onRouteChange, onLogout, user }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-16 items-center border-b border-slate-200 px-5">
          <div>
            <div className="text-sm font-semibold uppercase tracking-wide text-teal-700">AISM</div>
            <div className="text-xs text-slate-500">Instagram SEO manager</div>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.route}
              type="button"
              onClick={() => onRouteChange(item.route)}
              className={`h-9 w-full rounded-md px-3 text-left text-sm transition ${
                currentRoute === item.route
                  ? "bg-teal-50 font-medium text-teal-800"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="flex min-h-16 flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold text-slate-950">
                {NAV_ITEMS.find((item) => item.route === currentRoute)?.label}
              </h1>
              <p className="truncate text-sm text-slate-500">{user.email}</p>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto lg:hidden">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.route}
                  type="button"
                  onClick={() => onRouteChange(item.route)}
                  className={`h-9 shrink-0 rounded-md px-3 text-sm ${
                    currentRoute === item.route ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="h-9 rounded-md border border-slate-300 px-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}

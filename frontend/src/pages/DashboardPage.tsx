import { useEffect, useState } from "react";
import { getDashboardSummary } from "../services/api";
import type { DashboardSummary } from "../types/api";

type DashboardPageProps = {
  token: string;
};

const SUMMARY_LABELS: Array<{ key: keyof DashboardSummary; label: string }> = [
  { key: "social_accounts", label: "Social Accounts" },
  { key: "content_assets", label: "Assets" },
  { key: "content_ideas", label: "Ideas" },
  { key: "generated_content", label: "Generated" },
  { key: "posts", label: "Posts" },
  { key: "scheduled_posts", label: "Scheduled" },
  { key: "published_posts", label: "Published" },
  { key: "comments", label: "Comments" },
  { key: "pending_approvals", label: "Approvals" },
  { key: "active_model_configs", label: "Active Models" },
];

export function DashboardPage({ token }: DashboardPageProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    getDashboardSummary(token)
      .then((data) => {
        if (isMounted) setSummary(data);
      })
      .catch((err) => {
        if (isMounted) setError(err instanceof Error ? err.message : "Dashboard request failed");
      });
    return () => {
      isMounted = false;
    };
  }, [token]);

  if (error) {
    return <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  }

  if (!summary) {
    return <p className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">Loading dashboard...</p>;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {SUMMARY_LABELS.map((item) => (
          <div key={item.key} className="rounded-md border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{item.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-950">{summary[item.key]}</p>
          </div>
        ))}
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-slate-200 bg-white p-5">
          <h2 className="text-base font-semibold">Publishing</h2>
          <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">Total</dt>
              <dd className="mt-1 text-xl font-semibold">{summary.posts}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Scheduled</dt>
              <dd className="mt-1 text-xl font-semibold">{summary.scheduled_posts}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Published</dt>
              <dd className="mt-1 text-xl font-semibold">{summary.published_posts}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-md border border-slate-200 bg-white p-5">
          <h2 className="text-base font-semibold">Review Queue</h2>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">Pending approvals</dt>
              <dd className="mt-1 text-xl font-semibold">{summary.pending_approvals}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Comments</dt>
              <dd className="mt-1 text-xl font-semibold">{summary.comments}</dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}

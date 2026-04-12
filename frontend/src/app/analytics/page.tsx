"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

const API = API_BASE;

interface Stats {
  total_projects: number;
  by_status: Record<string, number>;
  total_stages_completed: number;
  total_quotations: number;
  avg_pipeline_time_seconds: number | null;
}

interface MetricLine { name: string; value: string; }

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [metrics, setMetrics] = useState<MetricLine[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  async function load() {
    const token = localStorage.getItem("token");
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const [sRes, mRes] = await Promise.all([
        fetch(`${API}/api/v1/batch/stats`, { headers }),
        fetch(`${API}/metrics`),
      ]);
      if (sRes.ok) setStats(await sRes.json());
      if (mRes.ok) {
        const text = await mRes.text();
        setMetrics(text.trim().split("\n").filter(Boolean).map(l => {
          const parts = l.split(" ");
          return { name: parts[0], value: parts.slice(1).join(" ") };
        }));
      }
    } catch {}
    finally { setLoading(false); }
  }

  const SL: Record<string, string> = {
    created: "已创建", in_progress: "进行中", completed: "已完成",
    review_needed: "待审核", failed: "失败", archived: "已归档",
  };
  const SC: Record<string, string> = {
    created: "bg-gray-100 text-gray-700", in_progress: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700", review_needed: "bg-orange-100 text-orange-700",
    failed: "bg-red-100 text-red-700", archived: "bg-gray-100 text-gray-500",
  };

  const agentMetrics = metrics.filter(m => m.name.startsWith("agent_executions"));
  const httpTotal = metrics.filter(m => m.name.startsWith("http_requests_total")).reduce((s, m) => s + parseInt(m.value || "0"), 0);

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">数据看板</h1>
        <p className="text-sm text-gray-500">系统运营指标与项目统计</p>
      </header>
      <div className="px-6 py-6 max-w-7xl mx-auto space-y-6">
        {loading ? <p className="text-center py-16 text-gray-400 text-sm">加载中...</p> : (<>
          {stats && (
            <div className="grid grid-cols-5 gap-4">
              {[
                { label: "总项目数", val: stats.total_projects, color: "text-gray-900" },
                { label: "已完成阶段", val: stats.total_stages_completed, color: "text-green-600" },
                { label: "报价方案", val: stats.total_quotations, color: "text-indigo-600" },
                { label: "平均阶段耗时", val: stats.avg_pipeline_time_seconds ? `${stats.avg_pipeline_time_seconds.toFixed(1)}s` : "—", color: "text-gray-900" },
                { label: "API 请求数", val: httpTotal, color: "text-gray-900" },
              ].map(k => (
                <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-xs text-gray-500">{k.label}</p>
                  <p className={`text-3xl font-bold mt-1 ${k.color}`}>{k.val}</p>
                </div>
              ))}
            </div>
          )}
          {stats?.by_status && Object.keys(stats.by_status).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">项目状态分布</h2>
              <div className="flex gap-3 flex-wrap">
                {Object.entries(stats.by_status).map(([s, c]) => (
                  <div key={s} className={`px-4 py-3 rounded-lg ${SC[s] || "bg-gray-100"}`}>
                    <p className="text-2xl font-bold">{c}</p>
                    <p className="text-xs mt-0.5">{SL[s] || s}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {agentMetrics.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">Agent 执行统计</h2>
              <table className="w-full text-sm">
                <thead><tr className="text-xs text-gray-500 border-b"><th className="py-2 text-left">指标</th><th className="py-2 text-right">值</th></tr></thead>
                <tbody>
                  {agentMetrics.map((m, i) => (
                    <tr key={i} className={i % 2 ? "bg-gray-50" : ""}>
                      <td className="py-2 text-gray-700 font-mono text-xs">{m.name}</td>
                      <td className="py-2 text-right text-gray-900">{m.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <details className="bg-white rounded-xl border border-gray-200 p-6">
            <summary className="text-sm font-semibold text-gray-900 cursor-pointer">原始指标 ({metrics.length})</summary>
            <pre className="mt-4 text-xs text-gray-600 bg-gray-50 rounded-lg p-4 overflow-auto max-h-[400px] font-mono">
              {metrics.map(m => `${m.name} ${m.value}`).join("\n")}
            </pre>
          </details>
        </>)}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Overview {
  projects: { total: number; by_status: Record<string, number> };
  quotations: { total: number; avg_roi: number; avg_price: number };
  qa_issues: { total: number; by_severity: Record<string, number>; by_status: Record<string, number> };
  knowledge_base: { total_entries: number };
}

interface AgentPerf {
  agent_name: string;
  total_runs: number;
  success: number;
  failed: number;
  success_rate: number;
  avg_time_seconds: number;
  avg_confidence: number;
}

interface PipelineStats {
  total_pipelines: number;
  full_completions: number;
  completion_rate: number;
  avg_stages_completed: number;
  avg_pipeline_time_seconds: number;
  qa_pass_rate: number;
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [agents, setAgents] = useState<AgentPerf[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : "";
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/analytics/overview`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/analytics/agent-performance`, { headers }).then(r => r.json()),
      fetch(`${API}/api/v1/analytics/pipeline-stats`, { headers }).then(r => r.json()),
    ]).then(([o, a, p]) => {
      setOverview(o);
      setAgents(a.agents || []);
      setPipeline(p);
    }).catch(() => {})
    .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center min-h-screen text-gray-400">加载中...</div>;

  const STATUS_LABELS: Record<string, string> = {
    created: "已创建", in_progress: "进行中", completed: "已完成",
    review_needed: "待审核", failed: "失败", archived: "已归档",
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">数据分析看板</h1>
        <p className="text-sm text-gray-500 mt-0.5">系统运营指标与 Agent 性能分析</p>
      </header>

      <div className="px-6 py-6 max-w-7xl mx-auto space-y-6">
        {/* Top KPIs */}
        {overview && pipeline && (
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: "总项目数", value: overview.projects.total, icon: "📁", color: "text-gray-900" },
              { label: "总报价数", value: overview.quotations.total, icon: "💰", color: "text-green-600" },
              { label: "平均 ROI", value: `${overview.quotations.avg_roi}%`, icon: "📈", color: "text-indigo-600" },
              { label: "Pipeline 完成率", value: `${pipeline.completion_rate}%`, icon: "⚡", color: "text-blue-600" },
              { label: "QA 通过率", value: `${pipeline.qa_pass_rate}%`, icon: "✅", color: "text-green-600" },
            ].map(kpi => (
              <div key={kpi.label} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">{kpi.label}</span>
                  <span className="text-lg">{kpi.icon}</span>
                </div>
                <p className={`text-2xl font-bold mt-2 ${kpi.color}`}>{kpi.value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">
          {/* Project status breakdown */}
          {overview && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">项目状态分布</h2>
              <div className="space-y-3">
                {Object.entries(overview.projects.by_status).map(([status, count]) => {
                  const pct = overview.projects.total > 0 ? (count / overview.projects.total) * 100 : 0;
                  const colors: Record<string, string> = {
                    created: "bg-gray-400", in_progress: "bg-blue-500", completed: "bg-green-500",
                    review_needed: "bg-orange-500", failed: "bg-red-500", archived: "bg-gray-300",
                  };
                  return (
                    <div key={status}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">{STATUS_LABELS[status] || status}</span>
                        <span className="text-gray-900 font-medium">{count}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className={`h-2 rounded-full ${colors[status] || "bg-gray-400"}`}
                          style={{ width: `${Math.max(pct, 2)}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* QA issue breakdown */}
          {overview && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">QA 问题分布</h2>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">总问题</p>
                  <p className="text-xl font-bold text-gray-900">{overview.qa_issues.total}</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">知识库</p>
                  <p className="text-xl font-bold text-indigo-600">{overview.knowledge_base.total_entries}</p>
                </div>
              </div>
              <div className="space-y-2">
                {Object.entries(overview.qa_issues.by_severity).map(([sev, count]) => {
                  const colors: Record<string, string> = { P0: "bg-red-500", P1: "bg-orange-500", P2: "bg-yellow-500" };
                  return (
                    <div key={sev} className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${colors[sev] || "bg-gray-400"}`} />
                      <span className="text-sm text-gray-600 flex-1">{sev}</span>
                      <span className="text-sm font-medium text-gray-900">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Agent Performance Table */}
        {agents.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900">Agent 执行性能</h2>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500">
                  <th className="px-5 py-2.5 text-left">Agent</th>
                  <th className="px-5 py-2.5 text-right">执行次数</th>
                  <th className="px-5 py-2.5 text-right">成功率</th>
                  <th className="px-5 py-2.5 text-right">平均耗时</th>
                  <th className="px-5 py-2.5 text-right">平均置信度</th>
                  <th className="px-5 py-2.5 text-right">状态</th>
                </tr>
              </thead>
              <tbody>
                {agents.sort((a, b) => b.total_runs - a.total_runs).map((agent, i) => (
                  <tr key={agent.agent_name} className={i % 2 === 1 ? "bg-gray-50" : ""}>
                    <td className="px-5 py-2.5 text-gray-900 font-medium">{agent.agent_name}</td>
                    <td className="px-5 py-2.5 text-right text-gray-700">{agent.total_runs}</td>
                    <td className="px-5 py-2.5 text-right">
                      <span className={agent.success_rate >= 80 ? "text-green-600" : agent.success_rate >= 50 ? "text-orange-600" : "text-red-600"}>
                        {agent.success_rate}%
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-right text-gray-700">{agent.avg_time_seconds}s</td>
                    <td className="px-5 py-2.5 text-right text-gray-700">{(agent.avg_confidence * 100).toFixed(0)}%</td>
                    <td className="px-5 py-2.5 text-right">
                      {agent.failed > 0 && <span className="text-xs px-1.5 py-0.5 bg-red-50 text-red-600 rounded">{agent.failed} 失败</span>}
                      {agent.failed === 0 && <span className="text-xs px-1.5 py-0.5 bg-green-50 text-green-600 rounded">正常</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pipeline stats */}
        {pipeline && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Pipeline 统计</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Pipeline 总数", value: pipeline.total_pipelines },
                { label: "完整完成", value: pipeline.full_completions },
                { label: "平均完成阶段", value: `${pipeline.avg_stages_completed}/12` },
                { label: "平均耗时", value: `${(pipeline.avg_pipeline_time_seconds / 60).toFixed(1)} 分钟` },
              ].map(s => (
                <div key={s.label} className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">{s.label}</p>
                  <p className="text-lg font-bold text-gray-900 mt-1">{s.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

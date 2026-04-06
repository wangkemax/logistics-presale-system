"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { projects as pApi, quotations as qApi, type Project, type Quotation } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SchemeData {
  scheme_id: string;
  scheme_name: string;
  automation_level: string;
  summary: string;
  key_changes: string[];
  headcount: { total: number; vs_base: string };
  automation_equipment: string[];
  cost_summary: { total_capex: number; annual_opex: number };
  financial_indicators: { roi_percent: number; irr_percent: number; npv_at_8pct: number; payback_months: number };
  pros: string[];
  cons: string[];
  recommended_for: string;
}

interface Comparison {
  schemes: Record<string, SchemeData>;
  recommendation: { recommended_scheme: string; reason: string };
  comparison_matrix: any[];
}

export default function WorkbenchPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [selectedScheme, setSelectedScheme] = useState<string | null>(null);

  useEffect(() => { load(); }, [id]);

  async function load() {
    try {
      const [p, q] = await Promise.all([pApi.get(id), pApi.getQuotations(id)]);
      setProject(p);
      setQuotations(q);
    } catch { router.push("/"); }
  }

  async function handleGenerateComparison() {
    setGenerating(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE}/api/v1/projects/${id}/quotations/compare-schemes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Failed" }));
        throw new Error(body.detail || "Generation failed");
      }
      const data = await res.json();
      setComparison(data);
      await load(); // Refresh quotations
    } catch (e: any) { setError(e.message); }
    finally { setGenerating(false); }
  }

  if (!project) return <div className="flex items-center justify-center min-h-screen text-gray-400">加载中...</div>;

  const schemes = comparison ? Object.values(comparison.schemes).filter(s => !("error" in s)) : [];
  const rec = comparison?.recommendation;
  const detail = selectedScheme ? comparison?.schemes[selectedScheme] : null;

  const LEVEL_COLORS: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-blue-100 text-blue-700",
    high: "bg-purple-100 text-purple-700",
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3 mb-2">
          <Link href={`/projects/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← 项目详情</Link>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">方案对比工作台</h1>
            <p className="text-sm text-gray-500">{project.name}</p>
          </div>
          <button onClick={handleGenerateComparison} disabled={generating}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50">
            {generating ? "AI 生成中 (约60秒)..." : "生成 A/B/C 方案对比"}
          </button>
        </div>
      </header>

      <div className="px-6 py-6 max-w-7xl mx-auto">
        {error && <div className="mb-4 px-4 py-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">{error}</div>}

        {/* Recommendation banner */}
        {rec && (
          <div className="mb-6 px-5 py-4 bg-indigo-50 border border-indigo-200 rounded-xl">
            <p className="text-sm font-medium text-indigo-800">
              推荐方案: <span className="text-indigo-600 font-semibold">方案{rec.recommended_scheme}</span>
            </p>
            <p className="text-xs text-indigo-600 mt-1">{rec.reason}</p>
          </div>
        )}

        {/* Scheme cards */}
        {schemes.length > 0 ? (
          <>
            <div className="grid grid-cols-3 gap-4 mb-6">
              {schemes.map(s => {
                const isRec = rec?.recommended_scheme === s.scheme_id;
                return (
                  <button key={s.scheme_id} onClick={() => setSelectedScheme(s.scheme_id)}
                    className={`text-left p-5 rounded-xl border-2 transition ${
                      selectedScheme === s.scheme_id ? "border-indigo-400 bg-indigo-50" :
                      isRec ? "border-indigo-200 bg-white" : "border-gray-200 bg-white hover:bg-gray-50"
                    }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-base font-semibold text-gray-900">{s.scheme_name}</span>
                      {isRec && <span className="text-[10px] px-2 py-0.5 bg-indigo-600 text-white rounded-full">推荐</span>}
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${LEVEL_COLORS[s.automation_level] || "bg-gray-100 text-gray-600"}`}>
                      {s.automation_level === "low" ? "低自动化" : s.automation_level === "medium" ? "中自动化" : "高自动化"}
                    </span>
                    <p className="text-xs text-gray-500 mt-3 line-clamp-2">{s.summary}</p>

                    <div className="grid grid-cols-2 gap-3 mt-4">
                      <div>
                        <p className="text-[10px] text-gray-400">CAPEX</p>
                        <p className="text-sm font-semibold text-gray-900">
                          ¥{((s.cost_summary?.total_capex || 0) / 10000).toFixed(0)}万
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-400">年 OPEX</p>
                        <p className="text-sm font-semibold text-gray-900">
                          ¥{((s.cost_summary?.annual_opex || 0) / 10000).toFixed(0)}万
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-400">ROI</p>
                        <p className="text-sm font-semibold text-green-600">{s.financial_indicators?.roi_percent?.toFixed(1) || "—"}%</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-400">回本</p>
                        <p className="text-sm font-semibold text-gray-900">{s.financial_indicators?.payback_months || "—"}月</p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Detail panel */}
            {detail && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-4">{detail.scheme_name} — 详细信息</h3>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">关键变更</h4>
                    <ul className="space-y-1">
                      {(detail.key_changes || []).map((c, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-indigo-400 mt-0.5">•</span>{c}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">自动化设备</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {(detail.automation_equipment || []).map((e, i) => (
                        <span key={i} className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">{e}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6 mt-6">
                  <div>
                    <h4 className="text-sm font-medium text-green-700 mb-2">优势</h4>
                    <ul className="space-y-1">
                      {(detail.pros || []).map((p, i) => (
                        <li key={i} className="text-sm text-gray-600">✓ {p}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-red-700 mb-2">劣势</h4>
                    <ul className="space-y-1">
                      {(detail.cons || []).map((c, i) => (
                        <li key={i} className="text-sm text-gray-600">✗ {c}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500"><span className="font-medium text-gray-700">推荐客户画像:</span> {detail.recommended_for}</p>
                </div>

                <div className="flex gap-3 mt-6 pt-4 border-t border-gray-100">
                  <button onClick={() => handleExportScheme(detail.scheme_id)}
                    className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">
                    导出此方案报价 (Excel)
                  </button>
                </div>
              </div>
            )}

            {/* Comparison table */}
            {comparison?.comparison_matrix && (
              <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100">
                  <h3 className="text-sm font-medium text-gray-700">指标对比矩阵</h3>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500">指标</th>
                      <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">方案A</th>
                      <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">方案B</th>
                      <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500">方案C</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.comparison_matrix.map((row, i) => {
                      const labels: Record<string, string> = {
                        total_capex: "总投资 (CAPEX)",
                        annual_opex: "年运营成本 (OPEX)",
                        roi_percent: "ROI (%)",
                        irr_percent: "IRR (%)",
                        payback_months: "回本周期 (月)",
                        headcount: "人员编制",
                      };
                      const fmt = (v: any) => {
                        if (v === "—" || v === null || v === undefined) return "—";
                        if (typeof v === "number" && v > 10000) return `¥${(v/10000).toFixed(0)}万`;
                        if (typeof v === "number") return v.toFixed(1);
                        return String(v);
                      };
                      return (
                        <tr key={i} className={i % 2 === 1 ? "bg-gray-50" : ""}>
                          <td className="px-5 py-2.5 text-gray-700">{labels[row.metric] || row.metric}</td>
                          <td className="px-5 py-2.5 text-right text-gray-900">{fmt(row.scheme_A)}</td>
                          <td className="px-5 py-2.5 text-right text-gray-900">{fmt(row.scheme_B)}</td>
                          <td className="px-5 py-2.5 text-right text-gray-900">{fmt(row.scheme_C)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
            <p className="text-3xl mb-3">📊</p>
            <p className="text-gray-500 text-sm mb-1">点击上方按钮生成 A/B/C 三个方案</p>
            <p className="text-gray-400 text-xs">AI 将根据不同自动化水平生成经济型/均衡型/高端型方案对比</p>
          </div>
        )}

        {/* Existing quotations */}
        {quotations.length > 0 && !comparison && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">已有报价</h3>
            <div className="grid grid-cols-3 gap-4">
              {quotations.map(q => (
                <div key={q.id} className="bg-white rounded-lg border border-gray-200 p-4">
                  <p className="text-sm font-medium text-gray-900">{q.scheme_name} v{q.version}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-lg font-semibold text-gray-900">
                      {q.total_price ? `¥${(q.total_price / 10000).toFixed(0)}万` : "—"}
                    </span>
                    <span className="text-xs text-green-600">ROI {q.roi?.toFixed(1) || "—"}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  async function handleExportScheme(schemeId: string) {
    const q = quotations.find(q => q.scheme_name.includes(`方案${schemeId}`) || q.scheme_name.includes(schemeId));
    if (q) {
      await qApi.exportExcel(id, q.id);
    } else {
      alert("请先在报价 Tab 中确认方案已保存");
    }
  }
}

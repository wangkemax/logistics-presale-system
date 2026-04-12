"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { projects as api, quotations as qApi, llmProviders, type Project, type Stage, type QAIssue, type Quotation, API_BASE } from "@/lib/api";
import { useWebSocket } from "@/lib/useWebSocket";

const STAGE_NAMES = [
  "项目假设", "招标文件解析", "需求澄清", "数据分析",
  "知识库检索", "方案设计", "自动化推荐", "案例匹配",
  "成本建模", "风险评估", "标书撰写", "QA 审核",
];

const STAGE_ICONS = ["📋","📄","❓","📊","🔍","🏗️","🤖","📎","💰","⚠️","📝","✅"];

// ── Formatted stage output renderer ──
function StageOutputView({ data, stageNumber }: { data: any; stageNumber: number }) {
  if (!data || typeof data !== "object") return null;
  if (data.error) {
    return <div className="px-4 py-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">{data.error}</div>;
  }

  const renderVal = (v: any): string => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "string") return v;
    if (typeof v === "number") return v.toLocaleString();
    if (typeof v === "boolean") return v ? "是" : "否";
    if (Array.isArray(v)) return v.length > 0 ? v.map(i => typeof i === "string" ? i : JSON.stringify(i)).join(", ") : "—";
    return JSON.stringify(v);
  };

  // Helper: get field with multiple key fallbacks
  const g = (obj: any, ...keys: string[]) => {
    if (!obj || typeof obj !== "object") return undefined;
    for (const k of keys) {
      if (obj[k] !== undefined) return obj[k];
    }
    return undefined;
  };

  // Stage 1: Requirements (keys: requirements / no Chinese variant — S1 has _uploaded_text)
  if (stageNumber === 1 && (data.requirements || data._uploaded_text)) {
    return (
      <div className="space-y-4">
        {(data.executive_summary || data.执行摘要) && <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">{data.executive_summary || data.执行摘要}</p>}
        {(data.project_overview || data.项目概况) && (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.project_overview || data.项目概况).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
              <div key={k} className="text-sm"><span className="text-gray-500">{k}:</span> <span className="text-gray-900">{renderVal(v)}</span></div>
            ))}
          </div>
        )}
        {data.requirements && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">需求清单 ({data.requirements.length} 项)</p>
            <div className="space-y-1 max-h-[400px] overflow-auto">
              {data.requirements.slice(0, 30).map((r: any, i: number) => (
                <div key={i} className="flex items-start gap-2 text-sm py-1.5 px-3 rounded hover:bg-gray-50">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium mt-0.5 ${r.priority === "P0" ? "bg-red-100 text-red-700" : r.priority === "P1" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}>{r.priority}</span>
                  <span className="text-gray-800 flex-1">{r.description || r.描述}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Stage 4: Knowledge Base Retrieval
  if (stageNumber === 4 && (data.retrieved_knowledge || data.knowledge_count)) {
    const counts = data.knowledge_count || {};
    const totalRetrieved = (counts.automation || 0) + (counts.cost_model || 0) + (counts.logistics || 0);
    const rk = data.retrieved_knowledge || {};
    const keyPoints = data.key_data_points || [];
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="text-2xl font-bold text-blue-700">{counts.automation || 0}</div>
            <div className="text-xs text-blue-600">自动化案例</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="text-2xl font-bold text-green-700">{counts.cost_model || 0}</div>
            <div className="text-xs text-green-600">成本模型</div>
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <div className="text-2xl font-bold text-orange-700">{counts.logistics || 0}</div>
            <div className="text-xs text-orange-600">物流案例</div>
          </div>
        </div>
        {totalRetrieved === 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
            ⚠️ 知识库为空。先到 <Link href="/knowledge" className="underline font-medium">知识库页面</Link> 上传历史案例，下次跑 Pipeline 才能引用真实数据。
          </div>
        )}
        {keyPoints.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">📌 关键数据点 ({keyPoints.length})</p>
            <div className="space-y-1">
              {keyPoints.slice(0, 10).map((p: any, i: number) => (
                <div key={i} className="text-sm py-2 px-3 bg-gray-50 rounded-lg">
                  <div className="text-xs text-gray-500">{p.type} · 来源: {p.source}</div>
                  <div className="text-gray-900 mt-0.5">{p.value}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {data.synthesized_context && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <p className="text-sm font-medium text-indigo-800 mb-2">综合分析</p>
            <p className="text-sm text-indigo-700 whitespace-pre-wrap leading-relaxed">{data.synthesized_context}</p>
          </div>
        )}
        {(rk.automation_cases || rk.cost_benchmarks || rk.logistics_cases) && (
          <details className="border border-gray-200 rounded-lg">
            <summary className="px-4 py-3 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50">
              查看详细检索内容
            </summary>
            <div className="p-4 space-y-3 text-sm text-gray-700">
              {rk.automation_cases && (
                <div><p className="font-medium text-gray-900 mb-1">自动化案例</p><div className="whitespace-pre-wrap">{rk.automation_cases}</div></div>
              )}
              {rk.cost_benchmarks && (
                <div><p className="font-medium text-gray-900 mb-1">成本基准</p><div className="whitespace-pre-wrap">{rk.cost_benchmarks}</div></div>
              )}
              {rk.logistics_cases && (
                <div><p className="font-medium text-gray-900 mb-1">物流案例</p><div className="whitespace-pre-wrap">{rk.logistics_cases}</div></div>
              )}
            </div>
          </details>
        )}
      </div>
    );
  }

  // Stage 10: Tender chapters (S10 uses English keys from tender_writer)
  if (stageNumber === 10 && data.document_structure) {
    return (
      <div className="space-y-4">
        {data.executive_summary && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <p className="text-sm font-medium text-indigo-800 mb-1">执行摘要</p>
            <p className="text-sm text-indigo-700 whitespace-pre-wrap">{data.executive_summary}</p>
          </div>
        )}
        <p className="text-sm text-gray-500">共 {data.chapters_completed || data.document_structure.length} 章, {data.total_word_count?.toLocaleString() || "—"} 字</p>
        {data.document_structure.map((ch: any) => (
          <details key={ch.chapter} className="border border-gray-200 rounded-lg">
            <summary className="px-4 py-3 text-sm font-medium text-gray-900 cursor-pointer hover:bg-gray-50">
              第{ch.chapter}章 {ch.title} <span className="text-xs text-gray-400 ml-2">{ch.word_count} 字</span>
            </summary>
            <div className="px-4 pb-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{ch.content}</div>
          </details>
        ))}
      </div>
    );
  }

  // Stage 5: Solution Design (Chinese: 执行摘要/仓库设计/人员配置/绩效指标)
  const s5summary = g(data, "executive_summary", "执行摘要");
  const s5warehouse = g(data, "warehouse_design", "仓库设计");
  const s5staffing = g(data, "staffing", "人员配置");
  const s5perf = g(data, "performance", "绩效指标");
  if (stageNumber === 5 && (s5summary || s5warehouse)) {
    const area = g(s5warehouse, "total_area_sqm", "总面积平方米", "总面积平米", "总面积");
    const headcount = g(s5staffing, "total_headcount", "总人数");
    const accuracy = g(s5perf, "accuracy_target", "准确率目标");
    return (
      <div className="space-y-4">
        {s5summary && <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg border border-blue-100">{s5summary}</p>}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "仓库面积", val: area ? `${Number(area).toLocaleString()} ㎡` : "—" },
            { label: "人员编制", val: headcount || "—" },
            { label: "准确率", val: accuracy || "—" },
          ].map(k => (
            <div key={k.label} className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-gray-900">{k.val}</p>
              <p className="text-xs text-gray-500">{k.label}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-indigo-600 cursor-pointer hover:underline" onClick={() => window.location.href = window.location.pathname + '/solution'}>
          → 点击查看完整方案设计工作台
        </p>
      </div>
    );
  }

  // Stage 6: Automation (Chinese: 推荐方案/自动化水平/总自动化投资)
  const s6recs = g(data, "recommendations", "推荐方案");
  if (stageNumber === 6 && s6recs) {
    const recsArr = Array.isArray(s6recs) ? s6recs : [];
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-600">自动化等级: <span className="font-medium text-gray-900">{g(data, "automation_level", "自动化水平") || "—"}</span></p>
        {g(data, "total_automation_investment", "总自动化投资") && (
          <p className="text-sm text-gray-600">总投资: <span className="font-medium text-gray-900">¥{(Number(g(data, "total_automation_investment", "总自动化投资")) / 10000).toFixed(0)}万</span></p>
        )}
        {recsArr.slice(0, 6).map((rec: any, i: number) => (
          <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900">{rec.technology || rec.技术 || rec.name || rec.名称}</span>
              <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded">{rec.suitability_score || rec.适配度评分 || "—"}/10</span>
            </div>
            <p className="text-xs text-gray-500">{rec.application_area || rec.应用场景 || ""}</p>
            <div className="flex gap-4 mt-1 text-xs text-gray-500">
              {(rec.estimated_cost_cny || rec.预估投资) && <span>投资 ¥{(Number(rec.estimated_cost_cny || rec.预估投资) / 10000).toFixed(0)}万</span>}
              {(rec.roi_percent || rec.投资回报率) && <span>ROI {rec.roi_percent || rec.投资回报率}%</span>}
              {(rec.payback_months || rec.回本周期) && <span>回本 {rec.payback_months || rec.回本周期}月</span>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Stage 8: Cost Model (Chinese: 财务指标/定价模型)
  const s8fi = g(data, "financial_indicators", "财务指标");
  const s8pricing = g(data, "pricing", "定价模型", "报价");
  if (stageNumber === 8 && s8fi) {
    const roi = g(s8fi, "roi_percent", "投资回报率", "ROI");
    const irr = g(s8fi, "irr_percent", "内部收益率", "IRR");
    const npv = g(s8fi, "npv_at_8pct", "净现值8折现", "净现值", "NPV");
    const payback = g(s8fi, "payback_months", "回本周期月数", "回本周期");
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "ROI", val: roi != null ? `${Number(roi).toFixed(1)}%` : "—", color: "text-green-600" },
            { label: "IRR", val: irr != null ? `${Number(irr).toFixed(1)}%` : "—", color: "text-blue-600" },
            { label: "NPV", val: npv != null ? `¥${(Number(npv) / 10000).toFixed(0)}万` : "—", color: "text-purple-600" },
            { label: "回本周期", val: payback != null ? `${payback}个月` : "—", color: "text-gray-900" },
          ].map(k => (
            <div key={k.label} className="bg-gray-50 rounded-lg p-3 text-center">
              <p className={`text-xl font-bold ${k.color}`}>{k.val}</p>
              <p className="text-xs text-gray-500">{k.label}</p>
            </div>
          ))}
        </div>
        {s8pricing && (
          <div className="text-sm space-y-1">
            {Object.entries(s8pricing).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
              <div key={k} className="flex gap-2"><span className="text-gray-500">{k}:</span> <span className="text-gray-900">{renderVal(v)}</span></div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Stage 9: Risk (Chinese: 风险矩阵/整体风险等级/前三大风险)
  const s9matrix = g(data, "risk_matrix", "风险矩阵");
  const s9level = g(data, "overall_risk_level", "整体风险等级");
  if (stageNumber === 9 && (s9matrix || s9level)) {
    const matrixArr = Array.isArray(s9matrix) ? s9matrix : [];
    return (
      <div className="space-y-3">
        <div className={`px-3 py-2 rounded-lg text-sm font-medium ${
          s9level === "LOW" || s9level === "低" ? "bg-green-50 text-green-700" :
          s9level === "HIGH" || s9level === "高" ? "bg-red-50 text-red-700" :
          "bg-orange-50 text-orange-700"
        }`}>风险等级: {s9level || "—"}</div>
        {matrixArr.slice(0, 8).map((r: any, i: number) => (
          <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-gray-50">
            <span className={`text-xs px-1.5 py-0.5 rounded mt-0.5 ${
              (r.impact === "HIGH" || r.影响 === "高") ? "bg-red-100 text-red-700" :
              (r.impact === "MEDIUM" || r.影响 === "中") ? "bg-orange-100 text-orange-700" :
              "bg-green-100 text-green-700"
            }`}>{r.likelihood || r.可能性 || "?"}/{r.impact || r.影响 || "?"}</span>
            <div>
              <p className="text-gray-800">{r.description || r.描述 || r.风险描述}</p>
              {(r.mitigation || r.缓解措施) && <p className="text-xs text-gray-500 mt-0.5">缓解: {r.mitigation || r.缓解措施}</p>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Stage 11: QA verdict (Chinese: 整体判决/总结/P0问题数量/问题清单)
  const s11verdict = g(data, "overall_verdict", "整体判决");
  if (stageNumber === 11 && s11verdict) {
    const p0 = g(data, "p0_count", "P0问题数量") || 0;
    const p1 = g(data, "p1_count", "P1问题数量") || 0;
    const p2 = g(data, "p2_count", "P2问题数量") || 0;
    const summary = g(data, "summary", "总结");
    const issues = g(data, "issues", "问题清单") || [];
    const issuesArr = Array.isArray(issues) ? issues : [];
    return (
      <div className="space-y-4">
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${(s11verdict === "PASS" || s11verdict === "通过") ? "bg-green-50 text-green-800 border border-green-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
          判定: {s11verdict} — P0: {p0}, P1: {p1}, P2: {p2}
        </div>
        {summary && <p className="text-sm text-gray-700">{summary}</p>}
        <div className="space-y-2">
          {issuesArr.slice(0, 20).map((iss: any, i: number) => (
            <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-gray-50">
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium mt-0.5 ${(iss.severity || iss.严重度) === "P0" ? "bg-red-100 text-red-700" : (iss.severity || iss.严重度) === "P1" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"}`}>{iss.severity || iss.严重度}</span>
              <div className="flex-1">
                <p className="text-gray-800">{iss.description || iss.描述}</p>
                {(iss.suggestion || iss.建议) && <p className="text-xs text-gray-500 mt-0.5">建议: {iss.suggestion || iss.建议}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Generic: render top-level keys as sections
  const skipKeys = ["_confidence", "_uploaded_text", "file_name", "file_count"];
  const entries = Object.entries(data).filter(([k]) => !skipKeys.includes(k));

  return (
    <div className="space-y-3 max-h-[600px] overflow-auto">
      {data._confidence !== undefined && (
        <p className="text-xs text-gray-400">置信度: {(data._confidence * 100).toFixed(0)}%</p>
      )}
      {entries.map(([key, value]) => {
        if (typeof value === "string" && value.length > 100) {
          return (
            <details key={key} className="border border-gray-200 rounded-lg">
              <summary className="px-4 py-2 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50">{key}</summary>
              <div className="px-4 pb-3 text-sm text-gray-700 whitespace-pre-wrap">{value}</div>
            </details>
          );
        }
        if (Array.isArray(value) && value.length > 0) {
          return (
            <details key={key} className="border border-gray-200 rounded-lg" open={value.length <= 5}>
              <summary className="px-4 py-2 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50">{key} ({value.length})</summary>
              <div className="px-4 pb-3 space-y-1">
                {value.slice(0, 20).map((item, i) => (
                  <div key={i} className="text-sm text-gray-700 py-1 border-b border-gray-50">
                    {typeof item === "string" ? item : typeof item === "object" ? (
                      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">{Object.entries(item).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
                        <div key={k}><span className="text-gray-500 text-xs">{k}:</span> <span className="text-gray-800 text-xs">{renderVal(v)}</span></div>
                      ))}</div>
                    ) : renderVal(item)}
                  </div>
                ))}
              </div>
            </details>
          );
        }
        if (typeof value === "object" && value !== null && !Array.isArray(value)) {
          return (
            <details key={key} className="border border-gray-200 rounded-lg">
              <summary className="px-4 py-2 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50">{key}</summary>
              <div className="px-4 pb-3 grid grid-cols-2 gap-x-4 gap-y-1">
                {Object.entries(value).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
                  <div key={k} className="text-sm"><span className="text-gray-500">{k}:</span> <span className="text-gray-900 ml-1">{renderVal(v)}</span></div>
                ))}
              </div>
            </details>
          );
        }
        return (
          <div key={key} className="flex gap-3 text-sm px-1">
            <span className="text-gray-500 min-w-[120px]">{key}:</span>
            <span className="text-gray-900">{renderVal(value)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [qaIssues, setQaIssues] = useState<QAIssue[]>([]);
  const [selectedStage, setSelectedStage] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [language, setLanguage] = useState<"zh" | "en" | "bilingual">("zh");
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [providers, setProviders] = useState<any[]>([]);
  const [tab, setTab] = useState<"pipeline" | "quotation" | "qa" | "documents" | "quality">("pipeline");
  const [qualityReport, setQualityReport] = useState<any>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const [generatingQuote, setGeneratingQuote] = useState(false);
  const [generatingDoc, setGeneratingDoc] = useState<string | null>(null);

  // ── WebSocket: real-time stage updates ──
  const onStageStarted = useCallback((stageNum: number, data: any) => {
    setStages(prev => prev.map(s =>
      s.stage_number === stageNum ? { ...s, status: "running" } : s
    ));
    setSelectedStage(stageNum);
    showToast(`Stage ${stageNum} 开始: ${data?.stage_name || STAGE_NAMES[stageNum]}`);
  }, []);

  const onStageCompleted = useCallback((stageNum: number, data: any) => {
    setStages(prev => prev.map(s =>
      s.stage_number === stageNum
        ? { ...s, status: "completed", confidence: data?.confidence }
        : s
    ));
    showToast(`Stage ${stageNum} 完成 ✓`);
  }, []);

  const onStageFailed = useCallback((stageNum: number, data: any) => {
    setStages(prev => prev.map(s =>
      s.stage_number === stageNum
        ? { ...s, status: "failed", error_message: data?.error }
        : s
    ));
    showToast(`Stage ${stageNum} 失败: ${data?.error || "Unknown"}`);
  }, []);

  const onPipelineCompleted = useCallback((data: any) => {
    setProject(prev => prev ? { ...prev, status: data?.qa_verdict === "PASS" ? "completed" : "review_needed" } : prev);
    showToast(`流水线完成! QA 结果: ${data?.qa_verdict}`);
    loadProject(); // Full refresh to get all data
  }, []);

  const { connected } = useWebSocket({
    projectId: id,
    onStageStarted,
    onStageCompleted,
    onStageFailed,
    onPipelineCompleted,
  });

  function showToast(msg: string) {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(""), 4000);
  }

  useEffect(() => {
    loadProject();
    llmProviders.list().then(p => {
      setProviders(p);
      // Try to load saved default from settings
      let savedProvider = "";
      let savedModel = "";
      try {
        const saved = localStorage.getItem("default_llm");
        if (saved) {
          const parsed = JSON.parse(saved);
          savedProvider = parsed.provider || "";
          savedModel = parsed.model || "";
        }
      } catch {}
      // Verify saved provider is still available
      const savedProviderObj = p.find((x: any) => x.id === savedProvider && x.available);
      if (savedProviderObj) {
        setProvider(savedProvider);
        // Verify saved model exists in this provider
        const modelExists = savedProviderObj.models.some((m: any) => m.id === savedModel);
        setModel(modelExists ? savedModel : savedProviderObj.default_model);
      } else {
        // Fallback to first available provider
        const defaultProvider = p.find((x: any) => x.available);
        if (defaultProvider) {
          setProvider(defaultProvider.id);
          setModel(defaultProvider.default_model);
        }
      }
    }).catch(() => {});
  }, [id]);

  // Auto-poll when pipeline is running (recovers state after navigation)
  useEffect(() => {
    if (!project) return;
    const isRunning = project.status === "in_progress" || stages.some(s => s.status === "running");
    if (!isRunning) return;
    const timer = setInterval(() => loadProject(true), 5000);
    return () => clearInterval(timer);
  }, [project?.status, stages]);

  const statusRank: Record<string, number> = { pending: 0, running: 1, completed: 2, failed: 2 };

  async function loadProject(isPoll = false) {
    try {
      const [p, s, q] = await Promise.all([
        api.get(id), api.getStages(id), api.getQAIssues(id),
      ]);
      setProject(p);
      // Always use smart merge — never regress stage status
      setStages(prev => {
        if (prev.length === 0) return s; // First load, just set
        return s.map(newStage => {
          const old = prev.find(o => o.stage_number === newStage.stage_number);
          if (!old) return newStage;
          const oldRank = statusRank[old.status] ?? 0;
          const newRank = statusRank[newStage.status] ?? 0;
          if (newRank < oldRank) return old; // Don't regress
          return newStage;
        });
      });
      setQaIssues(q);
    } catch {
      if (!isPoll) router.push("/");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    try {
      await api.uploadTender(id, Array.from(fileList));
      showToast(`${fileList.length} 个文件上传成功`);
      await loadProject();
    } catch (err: any) { showToast("上传失败: " + err.message); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function handleRunPipeline() {
    setRunning(true);
    try {
      await api.runPipeline(id, language, provider, model);
      showToast("AI 分析已启动，请等待实时更新...");
      setProject(prev => prev ? { ...prev, status: "in_progress" } : prev);
    } catch (err: any) { showToast("启动失败: " + err.message); }
    finally { setRunning(false); }
  }

  async function handleResumePipeline() {
    setRunning(true);
    try {
      const res = await api.resumePipeline(id);
      showToast(res.message || "从断点恢复中...");
      setProject(prev => prev ? { ...prev, status: "in_progress" } : prev);
    } catch (err: any) { showToast("恢复失败: " + err.message); }
    finally { setRunning(false); }
  }

  // Auto-poll when pipeline is running (fallback for WebSocket)
  useEffect(() => {
    if (project?.status !== "in_progress") return;
    const timer = setInterval(() => { loadProject(); }, 5000);
    return () => clearInterval(timer);
  }, [project?.status]);

  async function handleGenerateQuotation() {
    setGeneratingQuote(true);
    try {
      await qApi.generateFromPipeline(id);
      showToast("报价已生成");
      await loadProject();
    } catch (err: any) { showToast("生成失败: " + err.message); }
    finally { setGeneratingQuote(false); }
  }

  async function handleExportExcel(quotationId: string) {
    try {
      await qApi.exportExcel(id, quotationId);
      showToast("Excel 报价单已下载");
    } catch (err: any) { showToast("导出失败: " + err.message); }
  }

  async function handleGenerateDoc(docType: string) {
    setGeneratingDoc(docType);
    try {
      const token = localStorage.getItem("token");
      const apiBase = API_BASE;
      const res = await fetch(
        `${apiBase}/api/v1/projects/${id}/documents/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ doc_type: docType }),
        }
      );
      if (!res.ok) throw new Error("Generation failed");

      // Determine correct MIME type and extension
      const extMap: Record<string, { ext: string; mime: string }> = {
        tender: { ext: "docx", mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
        ppt: { ext: "pptx", mime: "application/vnd.openxmlformats-officedocument.presentationml.presentation" },
        pdf: { ext: "pdf", mime: "application/pdf" },
      };
      const { ext, mime } = extMap[docType] || { ext: "bin", mime: "application/octet-stream" };

      const rawBlob = await res.blob();
      // Re-create blob with correct MIME type to prevent browser confusion
      const blob = new Blob([rawBlob], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.name || "document"}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`${docType === "ppt" ? "PPT" : docType === "pdf" ? "PDF" : "标书"} 已下载`);
    } catch (err: any) { showToast("生成失败: " + err.message); }
    finally { setGeneratingDoc(null); }
  }

  if (!project) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">加载中...</div>;
  }

  const completedStages = stages.filter(s => s.status === "completed").length;
  const runningStage = stages.find(s => s.status === "running");
  const selected = selectedStage !== null ? stages.find(s => s.stage_number === selectedStage) : null;
  const p0Count = qaIssues.filter(i => i.severity === "P0").length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-4 right-4 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg max-w-sm animate-in fade-in">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">← 返回</Link>
            {connected && <span className="w-2 h-2 bg-green-400 rounded-full" title="WebSocket 已连接" />}
            {!connected && project.status === "in_progress" && <span className="w-2 h-2 bg-red-400 rounded-full" title="WebSocket 未连接" />}
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">{project.name}</h1>
              <p className="text-sm text-gray-500">{project.client_name || "未指定客户"} · {project.industry || ""}</p>
            </div>
            <div className="flex items-center gap-3">
              <Link href={`/projects/${id}/workbench`}
                className="px-4 py-2 text-sm text-indigo-600 border border-indigo-300 rounded-lg hover:bg-indigo-50 transition">
                📊 方案对比
              </Link>
              <Link href={`/projects/${id}/solution`}
                className="px-4 py-2 text-sm text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50 transition">
                🏗️ 方案详情
              </Link>
              <Link href={`/projects/${id}/quotation`}
                className="px-4 py-2 text-sm text-green-600 border border-green-300 rounded-lg hover:bg-green-50 transition">
                💰 报价计算
              </Link>
              <Link href={`/projects/${id}/qa`}
                className="px-4 py-2 text-sm text-orange-600 border border-orange-300 rounded-lg hover:bg-orange-50 transition">
                ✅ QA 审核
              </Link>
              <Link href={`/projects/${id}/editor`}
                className="px-4 py-2 text-sm text-purple-600 border border-purple-300 rounded-lg hover:bg-purple-50 transition">
                ✏️ 标书编辑
              </Link>
              <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv" multiple className="hidden" onChange={handleUpload} />
              <button onClick={() => fileRef.current?.click()} disabled={uploading}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50">
                {uploading ? "上传中..." : "上传招标文件"}
              </button>
              {stages.some(s => s.status === "failed") && project.status !== "in_progress" && (
                <button onClick={handleResumePipeline} disabled={running}
                  className="px-4 py-2 text-sm bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 transition disabled:opacity-50">
                  从断点恢复
                </button>
              )}
              <select value={language} onChange={e => setLanguage(e.target.value as "zh" | "en" | "bilingual")}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg outline-none bg-white">
                <option value="zh">中文输出</option>
                <option value="en">English</option>
                <option value="bilingual">中英双语</option>
              </select>
              <select value={provider} onChange={e => {
                  setProvider(e.target.value);
                  const p = providers.find((x: any) => x.id === e.target.value);
                  if (p) setModel(p.default_model);
                }}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg outline-none bg-white">
                {providers.map((p: any) => (
                  <option key={p.id} value={p.id} disabled={!p.available}>
                    {p.label}{!p.available ? " (未配置)" : ""}
                  </option>
                ))}
              </select>
              {providers.find((p: any) => p.id === provider)?.models?.length > 1 && (
                <select value={model} onChange={e => setModel(e.target.value)}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg outline-none bg-white">
                  {providers.find((p: any) => p.id === provider)?.models?.map((m: any) => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              )}
              <button onClick={handleRunPipeline} disabled={running || project.status === "in_progress"}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50">
                {project.status === "in_progress" ? "运行中..." : "启动 AI 分析"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Progress bar */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-gray-700">
              流水线进度: {completedStages} / 12 阶段
              {runningStage && <span className="text-blue-600 ml-2 animate-pulse">● 正在执行: {STAGE_NAMES[runningStage.stage_number]}</span>}
            </p>
            <p className="text-xs text-gray-400">{Math.round((completedStages / 12) * 100)}%</p>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5">
            <div className="bg-indigo-500 h-2.5 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${(completedStages / 12) * 100}%` }} />
          </div>
          {/* Mini stage indicators */}
          <div className="flex justify-between mt-3">
            {STAGE_NAMES.map((name, i) => {
              const s = stages.find(st => st.stage_number === i);
              const status = s?.status || "pending";
              return (
                <button key={i} onClick={() => setSelectedStage(i)} title={name}
                  className={`w-7 h-7 rounded-full text-xs flex items-center justify-center transition-all ${
                    status === "completed" ? "bg-green-100 text-green-700" :
                    status === "running" ? "bg-blue-100 text-blue-700 animate-pulse" :
                    status === "failed" ? "bg-red-100 text-red-700" :
                    "bg-gray-100 text-gray-400"
                  } ${selectedStage === i ? "ring-2 ring-indigo-400" : ""}`}>
                  {STAGE_ICONS[i]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-lg border border-gray-200 p-1 w-fit">
          {([
            ["pipeline", "流水线"],
            ["quotation", "报价"],
            ["documents", "文档生成"],
            ["quality", "📊 质量分析"],
            ["qa", `QA (${qaIssues.length}${p0Count > 0 ? ` · ${p0Count} P0` : ""})`],
          ] as const).map(([key, label]) => (
            <button key={key} onClick={() => setTab(key as any)}
              className={`px-4 py-1.5 text-sm rounded-md transition ${
                tab === key ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}>{label}</button>
          ))}
        </div>

        {/* ═══ Pipeline Tab ═══ */}
        {tab === "pipeline" && (
          <div className="grid grid-cols-3 gap-6">
            <div className="col-span-1 space-y-2">
              {stages.map(stage => {
                const isRunning = stage.status === "running";
                return (
                  <button key={stage.stage_number} onClick={() => setSelectedStage(stage.stage_number)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition text-sm ${
                      selectedStage === stage.stage_number ? "border-indigo-300 bg-indigo-50" :
                      isRunning ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-white hover:bg-gray-50"
                    }`}>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <span className="text-base">{STAGE_ICONS[stage.stage_number]}</span>
                        <span className={`font-medium ${isRunning ? "text-blue-700" : ""}`}>
                          {STAGE_NAMES[stage.stage_number]}
                        </span>
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        stage.status === "completed" ? "bg-green-100 text-green-700" :
                        stage.status === "running" ? "bg-blue-100 text-blue-700 animate-pulse" :
                        stage.status === "failed" ? "bg-red-100 text-red-700" :
                        "bg-gray-100 text-gray-500"
                      }`}>{stage.status === "completed" ? "完成" : stage.status === "running" ? "运行中" : stage.status === "failed" ? "失败" : "待执行"}</span>
                    </div>
                    <div className="flex items-center justify-between mt-1 ml-7 text-xs text-gray-400">
                      {stage.confidence !== null && <span>置信度 {(stage.confidence * 100).toFixed(0)}%</span>}
                      {stage.execution_time_seconds != null && <span>{stage.execution_time_seconds.toFixed(1)}s</span>}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-6">
              {selected ? (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold flex items-center gap-2">
                      <span>{STAGE_ICONS[selected.stage_number]}</span>
                      Stage {selected.stage_number}: {STAGE_NAMES[selected.stage_number]}
                    </h3>
                    {selected.stage_number > 0 && selected.status !== "running" && (
                      <button
                        onClick={async () => {
                          if (!confirm(`确定重跑 Stage ${selected.stage_number} (${STAGE_NAMES[selected.stage_number]}) 吗？\n\n这将覆盖当前输出数据。`)) return;
                          try {
                            await api.runStage(id, selected.stage_number);
                            await loadProject();
                            alert(`Stage ${selected.stage_number} 重跑已开始`);
                          } catch (e: any) {
                            alert("重跑失败: " + e.message);
                          }
                        }}
                        className="text-xs px-3 py-1.5 bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 border border-amber-200"
                        title="单独重跑此 Stage"
                      >
                        🔄 重跑此 Stage
                      </button>
                    )}
                  </div>
                  {selected.qa_result && (
                    <div className={`mb-4 px-3 py-2 rounded-lg text-sm ${
                      selected.qa_result === "PASS" ? "bg-green-50 text-green-700 border border-green-200" :
                      selected.qa_result === "FAIL" ? "bg-red-50 text-red-700 border border-red-200" :
                      "bg-orange-50 text-orange-700 border border-orange-200"
                    }`}>QA: {selected.qa_result}</div>
                  )}
                  {selected.error_message && (
                    <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">{selected.error_message}</div>
                  )}
                  {selected.status === "running" && (
                    <div className="text-center py-12 text-blue-600">
                      <div className="text-3xl mb-3 animate-spin inline-block">⚙️</div>
                      <p className="text-sm">Agent 正在执行中...</p>
                    </div>
                  )}
                  {selected.output_data && !selected.output_data._uploaded_text && (
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-3">输出数据</p>
                      <StageOutputView data={selected.output_data} stageNumber={selected.stage_number} />
                    </div>
                  )}
                  {(!selected.output_data && selected.status === "pending") && (
                    <p className="text-gray-400 text-sm text-center py-12">该阶段尚未执行</p>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-400 py-16">
                  <p className="text-sm">点击左侧阶段查看详情</p>
                  <p className="text-xs mt-1">启动 AI 分析后，进度将实时更新</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ Quotation Tab ═══ */}
        {tab === "quotation" && (
          <div>
            <div className="flex justify-end mb-4">
              <button onClick={handleGenerateQuotation} disabled={generatingQuote}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50">
                {generatingQuote ? "生成中..." : "从 Pipeline 生成报价"}
              </button>
            </div>
            <div className="bg-white rounded-xl border border-gray-200">
              {project.quotations && project.quotations.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {project.quotations.map(q => (
                    <div key={q.id} className="p-5">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-gray-900">{q.scheme_name} <span className="text-gray-400 font-normal text-sm">v{q.version}</span></h3>
                        <button onClick={() => handleExportExcel(q.id)}
                          className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700">
                          导出 Excel
                        </button>
                      </div>
                      <div className="grid grid-cols-5 gap-4 text-sm">
                        {[
                          { label: "总报价", val: q.total_price ? `¥${(q.total_price / 10000).toFixed(1)}万` : "—", color: "text-gray-900" },
                          { label: "ROI", val: q.roi ? `${q.roi.toFixed(1)}%` : "—", color: "text-green-600" },
                          { label: "IRR", val: q.irr ? `${q.irr.toFixed(1)}%` : "—", color: "text-blue-600" },
                          { label: "NPV", val: q.npv ? `¥${(q.npv / 10000).toFixed(1)}万` : "—", color: "text-purple-600" },
                          { label: "回本周期", val: q.payback_months ? `${q.payback_months}个月` : "—", color: "text-gray-900" },
                        ].map(item => (
                          <div key={item.label}>
                            <p className="text-gray-500 text-xs">{item.label}</p>
                            <p className={`text-lg font-semibold ${item.color}`}>{item.val}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-400 py-12">运行 AI 分析后点击上方按钮生成报价</p>
              )}
            </div>
          </div>
        )}

        {/* ═══ Documents Tab ═══ */}
        {tab === "documents" && (
          <div>
            {/* Bundle download CTA */}
            <div className="mb-6 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold mb-1">📦 一键打包全部交付物</h3>
                  <p className="text-sm text-indigo-100">下载 Word 标书 + Excel 报价单 + PDF 方案 + 原始数据 JSON 的 ZIP 包，直接交付客户</p>
                </div>
                <button
                  onClick={async () => {
                    try {
                      setGeneratingDoc("bundle");
                      const token = localStorage.getItem("token");
                      const res = await fetch(
                        `${API_BASE}/api/v1/projects/${id}/export-bundle`,
                        { headers: { Authorization: `Bearer ${token}` } }
                      );
                      if (!res.ok) throw new Error("打包失败");
                      const blob = await res.blob();
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `${project?.name || "project"}_完整交付包.zip`;
                      a.click();
                      URL.revokeObjectURL(url);
                      showToast("打包下载完成");
                    } catch (e: any) {
                      alert("打包失败: " + e.message);
                    } finally {
                      setGeneratingDoc(null);
                    }
                  }}
                  disabled={generatingDoc !== null || completedStages < 10}
                  className="px-6 py-3 bg-white text-indigo-600 rounded-lg font-semibold hover:bg-indigo-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  {generatingDoc === "bundle" ? "打包中..." : completedStages < 10 ? "需完成 10+ 阶段" : "📥 下载 ZIP"}
                </button>
              </div>
            </div>

          <div className="grid grid-cols-2 gap-6">
            {[
              { type: "tender", icon: "📄", title: "投标文档 (Word)", desc: "10 章节专业标书，含公司介绍、方案设计、成本报价等", ext: ".docx" },
              { type: "ppt", icon: "📊", title: "方案汇报 (PPT)", desc: "12 页方案演示，含项目概览、方案设计、财务分析、实施计划等", ext: ".pptx" },
              { type: "pdf", icon: "📑", title: "项目报告 (PDF)", desc: "需求、方案、财务指标、风险分析的综合 PDF 报告", ext: ".pdf" },
            ].map(doc => (
              <div key={doc.type} className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="text-3xl mb-3">{doc.icon}</div>
                <h3 className="font-semibold text-gray-900 mb-1">{doc.title}</h3>
                <p className="text-sm text-gray-500 mb-4">{doc.desc}</p>
                <button onClick={() => handleGenerateDoc(doc.type)}
                  disabled={generatingDoc !== null || completedStages < 10}
                  className="w-full px-4 py-2.5 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition">
                  {generatingDoc === doc.type ? "生成中..." :
                   completedStages < 10 ? "需完成 10+ 阶段" : `生成 ${doc.ext}`}
                </button>
              </div>
            ))}
          </div>
          </div>
        )}

        {/* ═══ Quality Analysis Tab ═══ */}
        {tab === "quality" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">质量分析报告</h3>
                  <p className="text-xs text-gray-500 mt-0.5">基于规则的程序化质量检查（不消耗 LLM 调用）</p>
                </div>
                <button
                  onClick={async () => {
                    setQualityLoading(true);
                    try {
                      const r = await api.analyzeQuality(id);
                      setQualityReport(r);
                    } catch (e: any) {
                      alert("分析失败: " + e.message);
                    } finally {
                      setQualityLoading(false);
                    }
                  }}
                  disabled={qualityLoading}
                  className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50">
                  {qualityLoading ? "分析中..." : qualityReport ? "🔄 重新分析" : "▶️ 开始分析"}
                </button>
              </div>

              {!qualityReport && (
                <p className="text-sm text-gray-400 text-center py-12">
                  点击「开始分析」生成质量报告
                </p>
              )}

              {qualityReport && (
                <div className="space-y-6">
                  {/* Overall verdict */}
                  <div className={`rounded-xl p-5 border-2 ${
                    qualityReport.verdict === "PASS" ? "bg-green-50 border-green-300" :
                    qualityReport.verdict === "CONDITIONAL_PASS" ? "bg-yellow-50 border-yellow-300" :
                    "bg-red-50 border-red-300"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">总体评分</p>
                        <p className="text-4xl font-bold text-gray-900">{qualityReport.overall_score}</p>
                        <p className={`text-sm mt-1 font-medium ${
                          qualityReport.verdict === "PASS" ? "text-green-700" :
                          qualityReport.verdict === "CONDITIONAL_PASS" ? "text-yellow-700" : "text-red-700"
                        }`}>
                          {qualityReport.verdict === "PASS" ? "✅ 通过" :
                           qualityReport.verdict === "CONDITIONAL_PASS" ? "⚠️ 有条件通过" : "❌ 不通过"}
                        </p>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="px-4 py-2 bg-red-100 rounded-lg">
                          <div className="text-2xl font-bold text-red-700">{qualityReport.summary.p0_count}</div>
                          <div className="text-xs text-red-600">P0 致命</div>
                        </div>
                        <div className="px-4 py-2 bg-orange-100 rounded-lg">
                          <div className="text-2xl font-bold text-orange-700">{qualityReport.summary.p1_count}</div>
                          <div className="text-xs text-orange-600">P1 严重</div>
                        </div>
                        <div className="px-4 py-2 bg-yellow-100 rounded-lg">
                          <div className="text-2xl font-bold text-yellow-700">{qualityReport.summary.p2_count}</div>
                          <div className="text-xs text-yellow-600">P2 一般</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stage-by-stage scores */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">分阶段评分</h4>
                    <div className="space-y-3">
                      {qualityReport.stage_scores.map((s: any) => (
                        <div key={s.stage} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <span className="text-xs px-2 py-1 bg-gray-100 rounded font-mono">Stage {s.stage}</span>
                              <span className="font-medium text-gray-900">{s.name}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="w-32 bg-gray-100 rounded-full h-2">
                                <div className={`h-2 rounded-full ${
                                  s.score >= 80 ? "bg-green-500" :
                                  s.score >= 60 ? "bg-yellow-500" : "bg-red-500"
                                }`} style={{ width: `${s.score}%` }} />
                              </div>
                              <span className={`text-lg font-bold ${
                                s.score >= 80 ? "text-green-600" :
                                s.score >= 60 ? "text-yellow-600" : "text-red-600"
                              }`}>{s.score}</span>
                            </div>
                          </div>
                          {Object.keys(s.metrics).length > 0 && (
                            <div className="grid grid-cols-3 gap-2 text-xs text-gray-500 mb-2 pl-2">
                              {Object.entries(s.metrics).map(([k, v]) => (
                                <div key={k}>
                                  {k}: <span className="text-gray-700 font-medium">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {s.issues.length > 0 && (
                            <div className="space-y-1 mt-2">
                              {s.issues.map((issue: any, i: number) => (
                                <div key={i} className="flex items-start gap-2 text-sm">
                                  <span className={`text-xs px-1.5 py-0.5 rounded font-semibold mt-0.5 ${
                                    issue.severity === "P0" ? "bg-red-100 text-red-700" :
                                    issue.severity === "P1" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"
                                  }`}>{issue.severity}</span>
                                  <span className="text-gray-700">{issue.msg}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Cross-stage consistency */}
                  {qualityReport.consistency_issues.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">跨阶段一致性检查</h4>
                      <div className="space-y-2">
                        {qualityReport.consistency_issues.map((issue: any, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-sm p-3 bg-gray-50 rounded-lg">
                            <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
                              issue.severity === "P0" ? "bg-red-100 text-red-700" :
                              issue.severity === "P1" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"
                            }`}>{issue.severity}</span>
                            <span className="text-gray-700">{issue.msg}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ QA Tab ═══ */}
        {tab === "qa" && (
          <div className="bg-white rounded-xl border border-gray-200">
            {qaIssues.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-400">暂无 QA 问题</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {qaIssues.map(issue => (
                  <div key={issue.id} className="px-6 py-4">
                    <div className="flex items-start gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full mt-0.5 font-semibold ${
                        issue.severity === "P0" ? "bg-red-100 text-red-800" :
                        issue.severity === "P1" ? "bg-orange-100 text-orange-800" : "bg-yellow-100 text-yellow-800"
                      }`}>{issue.severity}</span>
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{issue.description}</p>
                        {issue.suggestion && <p className="text-xs text-gray-500 mt-1">建议: {issue.suggestion}</p>}
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-xs text-gray-400">Stage {issue.stage_number}</span>
                          {issue.category && <span className="text-xs text-gray-400">{issue.category}</span>}
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            issue.status === "open" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600"
                          }`}>{issue.status}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { projects as api, quotations as qApi, type Project, type Stage, type QAIssue, type Quotation } from "@/lib/api";
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

  // Special renderers for known stage types
  // Stage 1: Requirements
  if (stageNumber === 1 && data.requirements) {
    return (
      <div className="space-y-4">
        {data.executive_summary && <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">{data.executive_summary}</p>}
        {data.project_overview && (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.project_overview).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
              <div key={k} className="text-sm"><span className="text-gray-500">{k}:</span> <span className="text-gray-900">{renderVal(v)}</span></div>
            ))}
          </div>
        )}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">需求清单 ({data.requirements.length} 项)</p>
          <div className="space-y-1 max-h-[400px] overflow-auto">
            {data.requirements.slice(0, 30).map((r: any, i: number) => (
              <div key={i} className="flex items-start gap-2 text-sm py-1.5 px-3 rounded hover:bg-gray-50">
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium mt-0.5 ${r.priority === "P0" ? "bg-red-100 text-red-700" : r.priority === "P1" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}>{r.priority}</span>
                <span className="text-gray-800 flex-1">{r.description}</span>
                {r.clarity && <span className="text-xs text-gray-400">{r.clarity}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Stage 10: Tender chapters
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

  // Stage 5: Solution Design
  if (stageNumber === 5 && (data.executive_summary || data.warehouse_design)) {
    return (
      <div className="space-y-4">
        {data.executive_summary && <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg border border-blue-100">{data.executive_summary}</p>}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "仓库面积", val: data.warehouse_design?.total_area_sqm ? `${Number(data.warehouse_design.total_area_sqm).toLocaleString()} ㎡` : "—" },
            { label: "人员编制", val: data.staffing?.total_headcount || "—" },
            { label: "准确率", val: data.performance?.accuracy_target || "—" },
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

  // Stage 6: Automation
  if (stageNumber === 6 && data.recommendations) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-600">自动化等级: <span className="font-medium text-gray-900">{data.automation_level || "—"}</span></p>
        {data.recommendations.slice(0, 6).map((rec: any, i: number) => (
          <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900">{rec.technology || rec.name}</span>
              <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded">{rec.suitability_score}/10</span>
            </div>
            <p className="text-xs text-gray-500">{rec.application_area}</p>
            <div className="flex gap-4 mt-1 text-xs text-gray-500">
              {rec.estimated_cost_cny && <span>投资 ¥{(rec.estimated_cost_cny / 10000).toFixed(0)}万</span>}
              {rec.roi_percent && <span>ROI {rec.roi_percent}%</span>}
              {rec.payback_months && <span>回本 {rec.payback_months}月</span>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Stage 8: Cost Model
  if (stageNumber === 8 && data.financial_indicators) {
    const fi = data.financial_indicators;
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "ROI", val: fi.roi_percent ? `${fi.roi_percent.toFixed(1)}%` : "—", color: "text-green-600" },
            { label: "IRR", val: fi.irr_percent ? `${fi.irr_percent.toFixed(1)}%` : "—", color: "text-blue-600" },
            { label: "NPV", val: fi.npv_at_8pct ? `¥${(fi.npv_at_8pct / 10000).toFixed(0)}万` : "—", color: "text-purple-600" },
            { label: "回本周期", val: fi.payback_months ? `${fi.payback_months}个月` : "—", color: "text-gray-900" },
          ].map(k => (
            <div key={k.label} className="bg-gray-50 rounded-lg p-3 text-center">
              <p className={`text-xl font-bold ${k.color}`}>{k.val}</p>
              <p className="text-xs text-gray-500">{k.label}</p>
            </div>
          ))}
        </div>
        {data.pricing && (
          <div className="text-sm space-y-1">
            {Object.entries(data.pricing).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
              <div key={k} className="flex gap-2"><span className="text-gray-500">{k}:</span> <span className="text-gray-900">{renderVal(v)}</span></div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Stage 9: Risk
  if (stageNumber === 9 && (data.risk_matrix || data.overall_risk_level)) {
    return (
      <div className="space-y-3">
        <div className={`px-3 py-2 rounded-lg text-sm font-medium ${
          data.overall_risk_level === "LOW" ? "bg-green-50 text-green-700" :
          data.overall_risk_level === "HIGH" ? "bg-red-50 text-red-700" :
          "bg-orange-50 text-orange-700"
        }`}>风险等级: {data.overall_risk_level || "—"}</div>
        {(data.risk_matrix || []).slice(0, 8).map((r: any, i: number) => (
          <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-gray-50">
            <span className={`text-xs px-1.5 py-0.5 rounded mt-0.5 ${
              r.impact === "HIGH" ? "bg-red-100 text-red-700" : r.impact === "MEDIUM" ? "bg-orange-100 text-orange-700" : "bg-green-100 text-green-700"
            }`}>{r.likelihood}/{r.impact}</span>
            <div>
              <p className="text-gray-800">{r.description}</p>
              {r.mitigation && <p className="text-xs text-gray-500 mt-0.5">缓解: {r.mitigation}</p>}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Stage 11: QA verdict
  if (stageNumber === 11 && data.overall_verdict) {
    return (
      <div className="space-y-4">
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${data.overall_verdict === "PASS" ? "bg-green-50 text-green-800 border border-green-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
          判定: {data.overall_verdict} — P0: {data.p0_count}, P1: {data.p1_count}, P2: {data.p2_count}
        </div>
        {data.summary && <p className="text-sm text-gray-700">{data.summary}</p>}
        <div className="space-y-2">
          {(data.issues || []).slice(0, 20).map((iss: any, i: number) => (
            <div key={i} className="flex items-start gap-2 text-sm p-2 rounded bg-gray-50">
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium mt-0.5 ${iss.severity === "P0" ? "bg-red-100 text-red-700" : iss.severity === "P1" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"}`}>{iss.severity}</span>
              <div className="flex-1">
                <p className="text-gray-800">{iss.description}</p>
                {iss.suggestion && <p className="text-xs text-gray-500 mt-0.5">建议: {iss.suggestion}</p>}
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
  const [language, setLanguage] = useState<"zh" | "en">("zh");
  const [tab, setTab] = useState<"pipeline" | "quotation" | "qa" | "documents">("pipeline");
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

  useEffect(() => { loadProject(); }, [id]);

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
      await api.runPipeline(id, language);
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
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/projects/${id}/documents/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ doc_type: docType }),
        }
      );
      if (!res.ok) throw new Error("Generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.name || "document"}_${docType}.${docType === "ppt" ? "pptx" : docType === "pdf" ? "pdf" : "docx"}`;
      a.click();
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
              <select value={language} onChange={e => setLanguage(e.target.value as "zh" | "en")}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg outline-none bg-white">
                <option value="zh">中文输出</option>
                <option value="en">English</option>
              </select>
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

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
    const timer = setInterval(loadProject, 5000);
    return () => clearInterval(timer);
  }, [project?.status, stages]);

  async function loadProject() {
    try {
      const [p, s, q] = await Promise.all([
        api.get(id), api.getStages(id), api.getQAIssues(id),
      ]);
      setProject(p);
      setStages(s);
      setQaIssues(q);
    } catch { router.push("/"); }
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
      await api.runPipeline(id);
      showToast("AI 分析已启动，请等待实时更新...");
      setProject(prev => prev ? { ...prev, status: "in_progress" } : prev);
    } catch (err: any) { showToast("启动失败: " + err.message); }
    finally { setRunning(false); }
  }

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
      a.download = `${project?.name || "document"}_${docType}.${docType === "ppt" ? "pptx" : "docx"}`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`${docType === "ppt" ? "PPT" : "标书"} 已下载`);
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
                      <p className="text-sm font-medium text-gray-600 mb-2">输出数据</p>
                      <pre className="bg-gray-50 rounded-lg p-4 text-xs overflow-auto max-h-[500px] text-gray-700 border border-gray-200"
                        style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                        {JSON.stringify(selected.output_data, null, 2)}
                      </pre>
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

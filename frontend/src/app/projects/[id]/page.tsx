"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { projects as api, type Project, type Stage, type QAIssue } from "@/lib/api";

const STAGE_NAMES = [
  "项目假设", "招标文件解析", "需求澄清", "数据分析",
  "知识库检索", "方案设计", "自动化推荐", "案例匹配",
  "成本建模", "风险评估", "标书撰写", "QA 审核",
];

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  running: "◌",
  completed: "●",
  failed: "✕",
};

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
  const [tab, setTab] = useState<"pipeline" | "quotation" | "qa">("pipeline");

  useEffect(() => {
    loadProject();
  }, [id]);

  // Auto-refresh when pipeline is running
  useEffect(() => {
    if (project?.status !== "in_progress") return;
    const timer = setInterval(loadProject, 5000);
    return () => clearInterval(timer);
  }, [project?.status]);

  async function loadProject() {
    try {
      const [p, s, q] = await Promise.all([
        api.get(id),
        api.getStages(id),
        api.getQAIssues(id),
      ]);
      setProject(p);
      setStages(s);
      setQaIssues(q);
    } catch {
      router.push("/");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadTender(id, file);
      await loadProject();
    } catch (err: any) {
      alert("上传失败: " + err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleRunPipeline() {
    setRunning(true);
    try {
      await api.runPipeline(id);
      await loadProject();
    } catch (err: any) {
      alert("启动失败: " + err.message);
    } finally {
      setRunning(false);
    }
  }

  if (!project) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">加载中...</div>;
  }

  const completedStages = stages.filter((s) => s.status === "completed").length;
  const activeStage = stages.find((s) => s.status === "running");
  const selected = selectedStage !== null ? stages.find((s) => s.stage_number === selectedStage) : null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">← 返回</Link>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">{project.name}</h1>
              <p className="text-sm text-gray-500">
                {project.client_name || "未指定客户"} · {project.industry || ""}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={handleUpload} />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
              >
                {uploading ? "上传中..." : "上传招标文件"}
              </button>
              <button
                onClick={handleRunPipeline}
                disabled={running || project.status === "in_progress"}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
              >
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
              {activeStage && <span className="text-blue-600 ml-2">正在执行: {activeStage.stage_name}</span>}
            </p>
            <p className="text-xs text-gray-400">{Math.round((completedStages / 12) * 100)}%</p>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${(completedStages / 12) * 100}%` }}
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-lg border border-gray-200 p-1 w-fit">
          {([
            ["pipeline", "流水线"],
            ["quotation", "报价"],
            ["qa", `QA 问题 (${qaIssues.length})`],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-1.5 text-sm rounded-md transition ${
                tab === key ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Pipeline Tab */}
        {tab === "pipeline" && (
          <div className="grid grid-cols-3 gap-6">
            {/* Stage list */}
            <div className="col-span-1 space-y-2">
              {stages.map((stage) => (
                <button
                  key={stage.stage_number}
                  onClick={() => setSelectedStage(stage.stage_number)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition text-sm ${
                    selectedStage === stage.stage_number
                      ? "border-indigo-300 bg-indigo-50"
                      : "border-gray-200 bg-white hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className={`text-xs ${
                        stage.status === "completed" ? "text-green-500" :
                        stage.status === "running" ? "text-blue-500 animate-pulse" :
                        stage.status === "failed" ? "text-red-500" : "text-gray-300"
                      }`}>
                        {STATUS_ICONS[stage.status] || "○"}
                      </span>
                      <span className="font-medium">{STAGE_NAMES[stage.stage_number]}</span>
                    </span>
                    {stage.execution_time_seconds && (
                      <span className="text-xs text-gray-400">{stage.execution_time_seconds.toFixed(1)}s</span>
                    )}
                  </div>
                  {stage.confidence !== null && (
                    <div className="mt-1 ml-5 text-xs text-gray-400">置信度: {(stage.confidence * 100).toFixed(0)}%</div>
                  )}
                </button>
              ))}
            </div>

            {/* Stage detail */}
            <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-6">
              {selected ? (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold">
                      Stage {selected.stage_number}: {STAGE_NAMES[selected.stage_number]}
                    </h3>
                    <span className={`text-xs px-2.5 py-1 rounded-full ${
                      selected.status === "completed" ? "bg-green-100 text-green-700" :
                      selected.status === "failed" ? "bg-red-100 text-red-700" :
                      selected.status === "running" ? "bg-blue-100 text-blue-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>
                      {selected.status}
                    </span>
                  </div>

                  {selected.qa_result && (
                    <div className={`mb-4 px-3 py-2 rounded-lg text-sm ${
                      selected.qa_result === "PASS" ? "bg-green-50 text-green-700" :
                      selected.qa_result === "FAIL" ? "bg-red-50 text-red-700" :
                      "bg-orange-50 text-orange-700"
                    }`}>
                      QA 结果: {selected.qa_result}
                    </div>
                  )}

                  {selected.error_message && (
                    <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm">
                      {selected.error_message}
                    </div>
                  )}

                  {selected.output_data && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-gray-600 mb-2">输出数据</p>
                      <pre className="bg-gray-50 rounded-lg p-4 text-xs overflow-auto max-h-[500px] text-gray-700">
                        {JSON.stringify(selected.output_data, null, 2)}
                      </pre>
                    </div>
                  )}

                  {!selected.output_data && selected.status === "pending" && (
                    <p className="text-gray-400 text-sm">该阶段尚未执行</p>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-400 py-12">
                  <p>点击左侧阶段查看详情</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* QA Tab */}
        {tab === "qa" && (
          <div className="bg-white rounded-xl border border-gray-200">
            {qaIssues.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-400">暂无 QA 问题</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {qaIssues.map((issue) => (
                  <div key={issue.id} className="px-6 py-4">
                    <div className="flex items-start gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full mt-0.5 ${
                        issue.severity === "P0" ? "severity-p0" :
                        issue.severity === "P1" ? "severity-p1" : "severity-p2"
                      }`}>
                        {issue.severity}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{issue.description}</p>
                        {issue.suggestion && (
                          <p className="text-xs text-gray-500 mt-1">建议: {issue.suggestion}</p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          阶段 {issue.stage_number} · {issue.category} · {issue.status}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quotation Tab */}
        {tab === "quotation" && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            {project.quotations && project.quotations.length > 0 ? (
              <div className="space-y-6">
                {project.quotations.map((q) => (
                  <div key={q.id} className="border border-gray-200 rounded-lg p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold">{q.scheme_name} (v{q.version})</h3>
                      <span className={`text-xs px-2.5 py-1 rounded-full ${
                        q.status === "approved" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                      }`}>{q.status}</span>
                    </div>
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">总报价</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {q.total_price ? `¥${(q.total_price / 10000).toFixed(1)}万` : "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">ROI</p>
                        <p className="text-lg font-semibold text-green-600">{q.roi ? `${q.roi.toFixed(1)}%` : "—"}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">IRR</p>
                        <p className="text-lg font-semibold text-blue-600">{q.irr ? `${q.irr.toFixed(1)}%` : "—"}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">回本周期</p>
                        <p className="text-lg font-semibold text-gray-900">{q.payback_months ? `${q.payback_months}个月` : "—"}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-400 py-12">运行 AI 分析后将自动生成报价</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

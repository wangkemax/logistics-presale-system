"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { projects as pApi, type Project, type Stage, type QAIssue } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SEVERITY_CONFIG = {
  P0: { label: "致命", bg: "bg-red-100", text: "text-red-800", border: "border-red-200", dot: "bg-red-500" },
  P1: { label: "严重", bg: "bg-orange-100", text: "text-orange-800", border: "border-orange-200", dot: "bg-orange-500" },
  P2: { label: "一般", bg: "bg-yellow-100", text: "text-yellow-800", border: "border-yellow-200", dot: "bg-yellow-500" },
};

const STAGE_NAMES = [
  "项目假设","招标文件解析","需求澄清","数据分析","知识库检索",
  "方案设计","自动化推荐","案例匹配","成本建模","风险评估","标书撰写","QA审核",
];

export default function QAReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [issues, setIssues] = useState<QAIssue[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [filter, setFilter] = useState<string>("all"); // all / P0 / P1 / P2 / open / resolved
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");
  const [resolving, setResolving] = useState(false);
  const [rerunning, setRerunning] = useState<number | null>(null);

  useEffect(() => { load(); }, [id]);

  async function load() {
    try {
      const [p, q, s] = await Promise.all([
        pApi.get(id), pApi.getQAIssues(id), pApi.getStages(id),
      ]);
      setProject(p);
      setIssues(q);
      setStages(s);
    } catch {}
  }

  async function handleResolve(issueId: string) {
    if (!resolution.trim()) return;
    setResolving(true);
    try {
      await pApi.resolveQAIssue(id, issueId, resolution);
      setResolution("");
      setSelectedId(null);
      await load();
    } catch {}
    finally { setResolving(false); }
  }

  async function handleAccept(issueId: string) {
    try {
      const token = localStorage.getItem("token");
      await fetch(`${API_BASE}/api/v1/projects/${id}/qa-issues/${issueId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ resolution: "Accepted as-is", status: "accepted" }),
      });
      await load();
    } catch {}
  }

  async function handleRerunStage(stageNum: number) {
    setRerunning(stageNum);
    try {
      const token = localStorage.getItem("token");
      await fetch(`${API_BASE}/api/v1/projects/${id}/run-stage`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ stage_number: stageNum }),
      });
      await load();
    } catch {}
    finally { setRerunning(null); }
  }

  const filtered = issues.filter(i => {
    if (filter === "all") return true;
    if (filter === "open") return i.status === "open";
    if (filter === "resolved") return i.status !== "open";
    return i.severity === filter;
  });

  const p0Open = issues.filter(i => i.severity === "P0" && i.status === "open").length;
  const p1Open = issues.filter(i => i.severity === "P1" && i.status === "open").length;
  const totalOpen = issues.filter(i => i.status === "open").length;
  const totalResolved = issues.filter(i => i.status !== "open").length;

  const selected = filtered.find(i => i.id === selectedId);

  // Group issues by stage
  const stageIssues = new Map<number, QAIssue[]>();
  filtered.forEach(i => {
    const arr = stageIssues.get(i.stage_number) || [];
    arr.push(i);
    stageIssues.set(i.stage_number, arr);
  });

  const canPass = p0Open === 0;

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3 mb-2">
          <Link href={`/projects/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← 项目详情</Link>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">QA 质量审核</h1>
            <p className="text-sm text-gray-500">{project?.name || ""}</p>
          </div>
          <div className={`px-4 py-2 rounded-lg text-sm font-medium ${
            canPass ? "bg-green-100 text-green-700 border border-green-200" : "bg-red-100 text-red-700 border border-red-200"
          }`}>
            {canPass ? "✓ QA 可通过" : `✕ ${p0Open} 个 P0 问题待解决`}
          </div>
        </div>
      </header>

      <div className="px-6 py-6 max-w-7xl mx-auto">
        {/* Stats */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "总问题", val: issues.length, color: "text-gray-900", bg: "bg-white" },
            { label: "P0 致命", val: p0Open, color: p0Open > 0 ? "text-red-600" : "text-gray-400", bg: p0Open > 0 ? "bg-red-50" : "bg-white" },
            { label: "P1 严重", val: p1Open, color: p1Open > 0 ? "text-orange-600" : "text-gray-400", bg: "bg-white" },
            { label: "待处理", val: totalOpen, color: "text-blue-600", bg: "bg-white" },
            { label: "已解决", val: totalResolved, color: "text-green-600", bg: "bg-white" },
          ].map(s => (
            <div key={s.label} className={`${s.bg} border border-gray-200 rounded-lg p-3`}>
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color}`}>{s.val}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-1.5 mb-4">
          {[
            { key: "all", label: "全部" },
            { key: "P0", label: "P0" },
            { key: "P1", label: "P1" },
            { key: "P2", label: "P2" },
            { key: "open", label: "待处理" },
            { key: "resolved", label: "已解决" },
          ].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 text-xs rounded-lg transition ${
                filter === f.key ? "bg-indigo-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}>{f.label}</button>
          ))}
        </div>

        {/* Issue list grouped by stage */}
        <div className="space-y-4">
          {Array.from(stageIssues.entries())
            .sort(([a], [b]) => a - b)
            .map(([stageNum, stageIssueList]) => (
              <div key={stageNum} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">
                    Stage {stageNum}: {STAGE_NAMES[stageNum] || `Stage ${stageNum}`}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">{stageIssueList.length} 个问题</span>
                    <button onClick={() => handleRerunStage(stageNum)}
                      disabled={rerunning === stageNum}
                      className="text-xs px-2.5 py-1 bg-indigo-50 text-indigo-600 rounded hover:bg-indigo-100 disabled:opacity-50">
                      {rerunning === stageNum ? "重跑中..." : "重跑此阶段"}
                    </button>
                  </div>
                </div>
                <div className="divide-y divide-gray-100">
                  {stageIssueList.map(issue => {
                    const sev = SEVERITY_CONFIG[issue.severity as keyof typeof SEVERITY_CONFIG] || SEVERITY_CONFIG.P2;
                    const isSelected = selectedId === issue.id;
                    return (
                      <div key={issue.id}>
                        <button onClick={() => setSelectedId(isSelected ? null : issue.id)}
                          className={`w-full text-left px-5 py-3 hover:bg-gray-50 transition ${isSelected ? "bg-indigo-50" : ""}`}>
                          <div className="flex items-start gap-3">
                            <span className={`text-xs px-1.5 py-0.5 rounded font-semibold mt-0.5 ${sev.bg} ${sev.text}`}>
                              {issue.severity}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-gray-900">{issue.description}</p>
                              <div className="flex items-center gap-2 mt-1">
                                {issue.category && <span className="text-[10px] text-gray-400">{issue.category}</span>}
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                  issue.status === "open" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600"
                                }`}>{issue.status}</span>
                              </div>
                            </div>
                          </div>
                        </button>

                        {isSelected && (
                          <div className="px-5 pb-4 pt-1 bg-gray-50 border-t border-gray-100">
                            {issue.suggestion && (
                              <p className="text-sm text-gray-600 mb-3">
                                <span className="font-medium text-gray-700">建议: </span>{issue.suggestion}
                              </p>
                            )}
                            {issue.resolution && (
                              <p className="text-sm text-green-700 mb-3">
                                <span className="font-medium">解决方案: </span>{issue.resolution}
                              </p>
                            )}
                            {issue.status === "open" && (
                              <div className="flex gap-2">
                                <input value={resolution} onChange={e => setResolution(e.target.value)}
                                  placeholder="输入解决方案..."
                                  className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg outline-none" />
                                <button onClick={() => handleResolve(issue.id)} disabled={resolving || !resolution.trim()}
                                  className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                                  {resolving ? "..." : "标记解决"}
                                </button>
                                {issue.severity !== "P0" && (
                                  <button onClick={() => handleAccept(issue.id)}
                                    className="px-3 py-1.5 text-xs bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                                    接受风险
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
            <p className="text-3xl mb-2">🎉</p>
            <p className="text-gray-500 text-sm">
              {filter === "all" ? "暂无 QA 问题，运行流水线后将自动审核" : "没有匹配的问题"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

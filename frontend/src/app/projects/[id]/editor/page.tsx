"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

const API = API_BASE;

interface Chapter {
  chapter: number;
  title: string;
  content: string;
  word_count?: number;
}

type AIAction = "rewrite" | "expand" | "polish" | null;

const STYLES = [
  { id: "professional", label: "专业正式" },
  { id: "concise", label: "精简扼要" },
  { id: "detailed", label: "详细展开" },
  { id: "persuasive", label: "有说服力" },
];

const POLISH_FOCUS = [
  { id: "all", label: "全面优化" },
  { id: "grammar", label: "修正语法" },
  { id: "flow", label: "改善流畅度" },
  { id: "data", label: "优化数据呈现" },
  { id: "persuasion", label: "增强说服力" },
];

export default function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [aiAction, setAiAction] = useState<AIAction>(null);
  const [aiProcessing, setAiProcessing] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [style, setStyle] = useState("professional");
  const [polishFocus, setPolishFocus] = useState("all");
  const [instruction, setInstruction] = useState("");
  const [toast, setToast] = useState("");
  const [history, setHistory] = useState<string[]>([]);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : "";
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

  useEffect(() => { loadChapters(); }, [id]);

  async function loadChapters() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/projects/${id}/editor/chapters`, { headers });
      const data = await res.json();
      setChapters(data.chapters || []);
      if (data.chapters?.length > 0) {
        setSelectedIdx(0);
        setEditContent(data.chapters[0].content);
      }
    } catch {}
    finally { setLoading(false); }
  }

  function selectChapter(idx: number) {
    // Save current edits
    if (selectedIdx !== null) {
      setChapters(prev => prev.map((ch, i) => i === selectedIdx ? { ...ch, content: editContent } : ch));
    }
    setSelectedIdx(idx);
    setEditContent(chapters[idx].content);
    setAiResult(null);
    setAiAction(null);
    setHistory([]);
  }

  async function handleAIAction() {
    if (selectedIdx === null) return;
    const ch = chapters[selectedIdx];
    setAiProcessing(true);
    setAiResult(null);

    try {
      let endpoint = "";
      let body: any = {};

      if (aiAction === "rewrite") {
        endpoint = "rewrite";
        body = { chapter_title: ch.title, original_content: editContent, instruction: instruction || "改写得更专业", style };
      } else if (aiAction === "expand") {
        endpoint = "expand";
        body = { section_title: ch.title, brief_content: editContent, target_words: 800 };
      } else if (aiAction === "polish") {
        endpoint = "polish";
        body = { content: editContent, focus: polishFocus };
      }

      const res = await fetch(`${API}/api/v1/projects/${id}/editor/${endpoint}`, {
        method: "POST", headers, body: JSON.stringify(body),
      });
      const data = await res.json();

      const result = data.rewritten_content || data.expanded_content || data.polished_content || "";
      setAiResult(result);
      if (data.changes_summary) {
        showToast(`AI: ${data.changes_summary}`);
      }
    } catch (e: any) { showToast("AI 处理失败"); }
    finally { setAiProcessing(false); }
  }

  function acceptAIResult() {
    if (aiResult === null) return;
    setHistory(prev => [...prev, editContent]); // Save for undo
    setEditContent(aiResult);
    setAiResult(null);
    setAiAction(null);
    showToast("已采纳 AI 结果");
  }

  function undoLast() {
    if (history.length === 0) return;
    setEditContent(history[history.length - 1]);
    setHistory(prev => prev.slice(0, -1));
    showToast("已撤销");
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  function handleDownloadAll() {
    // Save current edits first
    const allChapters = chapters.map((ch, i) => i === selectedIdx ? { ...ch, content: editContent } : ch);
    const md = allChapters.map(ch => `# 第${ch.chapter}章 ${ch.title}\n\n${ch.content}`).join("\n\n---\n\n");
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tender_draft.md";
    a.click();
  }

  const selected = selectedIdx !== null ? chapters[selectedIdx] : null;

  return (
    <div className="min-h-screen flex flex-col">
      {toast && (
        <div className="fixed top-4 right-4 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg">{toast}</div>
      )}

      <header className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/projects/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← 返回</Link>
            <h1 className="text-base font-semibold text-gray-900">标书编辑器</h1>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={undoLast} disabled={history.length === 0}
              className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30">
              ↩ 撤销
            </button>
            <button onClick={handleDownloadAll}
              className="px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700">
              下载 Markdown
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Chapter list */}
        <div className="w-52 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0">
          <div className="p-3 text-xs font-medium text-gray-500 uppercase tracking-wider">章节</div>
          {loading ? (
            <p className="px-3 text-sm text-gray-400">加载中...</p>
          ) : chapters.length === 0 ? (
            <p className="px-3 text-sm text-gray-400">运行 Pipeline 后生成章节</p>
          ) : (
            chapters.map((ch, i) => (
              <button key={i} onClick={() => selectChapter(i)}
                className={`w-full text-left px-3 py-2.5 text-sm border-b border-gray-50 transition ${
                  selectedIdx === i ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-700 hover:bg-gray-50"
                }`}>
                <span className="text-xs text-gray-400">第{ch.chapter}章</span>
                <p className="truncate">{ch.title}</p>
              </button>
            ))
          )}
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          {selected ? (
            <>
              <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
                <div>
                  <p className="text-sm font-medium text-gray-900">第{selected.chapter}章 {selected.title}</p>
                  <p className="text-xs text-gray-400">{editContent.length} 字</p>
                </div>
                <div className="flex gap-1.5">
                  {(["rewrite", "expand", "polish"] as const).map(action => (
                    <button key={action} onClick={() => setAiAction(aiAction === action ? null : action)}
                      className={`px-3 py-1.5 text-xs rounded-lg transition ${
                        aiAction === action ? "bg-indigo-600 text-white" : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
                      }`}>
                      {action === "rewrite" ? "✨ AI 改写" : action === "expand" ? "📝 AI 扩展" : "💎 AI 润色"}
                    </button>
                  ))}
                </div>
              </div>

              {/* AI action panel */}
              {aiAction && (
                <div className="px-6 py-3 bg-indigo-50 border-b border-indigo-100 flex-shrink-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    {aiAction === "rewrite" && (
                      <>
                        <select value={style} onChange={e => setStyle(e.target.value)}
                          className="px-2 py-1 text-xs border border-indigo-200 rounded bg-white outline-none">
                          {STYLES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                        </select>
                        <input value={instruction} onChange={e => setInstruction(e.target.value)}
                          placeholder="改写指令 (可选)..."
                          className="flex-1 px-2 py-1 text-xs border border-indigo-200 rounded bg-white outline-none min-w-[200px]" />
                      </>
                    )}
                    {aiAction === "polish" && (
                      <select value={polishFocus} onChange={e => setPolishFocus(e.target.value)}
                        className="px-2 py-1 text-xs border border-indigo-200 rounded bg-white outline-none">
                        {POLISH_FOCUS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                      </select>
                    )}
                    <button onClick={handleAIAction} disabled={aiProcessing}
                      className="px-4 py-1 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                      {aiProcessing ? "处理中..." : "执行"}
                    </button>
                  </div>
                </div>
              )}

              <div className="flex flex-1 min-h-0">
                {/* Text editor */}
                <textarea
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  className={`${aiResult ? "w-1/2" : "w-full"} p-6 text-sm leading-relaxed text-gray-800 outline-none resize-none border-none bg-white font-sans`}
                  style={{ fontFamily: "'Noto Serif SC', serif", lineHeight: 1.9 }}
                />

                {/* AI result diff panel */}
                {aiResult && (
                  <div className="w-1/2 border-l border-gray-200 flex flex-col">
                    <div className="px-4 py-2 bg-green-50 border-b border-green-100 flex items-center justify-between flex-shrink-0">
                      <span className="text-xs font-medium text-green-700">AI 结果预览</span>
                      <div className="flex gap-1.5">
                        <button onClick={acceptAIResult}
                          className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700">
                          ✓ 采纳
                        </button>
                        <button onClick={() => setAiResult(null)}
                          className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
                          ✕ 放弃
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 p-6 overflow-y-auto text-sm leading-relaxed text-gray-800 bg-green-50/30"
                      style={{ fontFamily: "'Noto Serif SC', serif", lineHeight: 1.9 }}>
                      {aiResult}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <p className="text-sm">{chapters.length > 0 ? "选择左侧章节开始编辑" : "运行 Pipeline Stage 10 (标书撰写) 后可编辑"}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

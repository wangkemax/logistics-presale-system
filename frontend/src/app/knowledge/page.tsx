"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { knowledge as kApi, type KnowledgeEntry, type SearchResult } from "@/lib/api";

const CATEGORIES = [
  { id: "", label: "全部", icon: "📚" },
  { id: "automation_case", label: "自动化案例", icon: "🤖" },
  { id: "cost_model", label: "成本模型", icon: "💰" },
  { id: "logistics_case", label: "物流案例", icon: "🚛" },
];

export default function KnowledgePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [category, setCategory] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ category: "logistics_case", title: "", content: "", tags: "" });
  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({ project_name: "", client_name: "" });
  const [showUpload, setShowUpload] = useState(false);

  async function handleExcelUpload(file: File) {
    setUploading(true);
    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", file);
      const params = new URLSearchParams({
        project_name: uploadForm.project_name,
        client_name: uploadForm.client_name,
      });
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/knowledge/upload-roi-excel?${params}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "上传失败");
      }
      const result = await res.json();
      alert(`成功导入 ${result.imported} 条知识条目`);
      setShowUpload(false);
      setUploadForm({ project_name: "", client_name: "" });
      loadEntries();
    } catch (e: any) {
      alert("上传失败: " + e.message);
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => { loadEntries(); }, [category]);

  async function loadEntries() {
    setLoading(true);
    try {
      const data = await kApi.list(category || undefined);
      setEntries(data);
      setSearchResults(null);
    } catch {}
    finally { setLoading(false); }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const results = await kApi.search(searchQuery, category || undefined, 10);
      setSearchResults(results);
    } catch {}
    finally { setSearching(false); }
  }

  async function handleAdd() {
    if (!addForm.title || !addForm.content) return;
    try {
      const tags = addForm.tags.split(/[,，\s]+/).filter(Boolean);
      await kApi.create({ ...addForm, tags });
      setShowAdd(false);
      setAddForm({ category: "logistics_case", title: "", content: "", tags: "" });
      loadEntries();
    } catch (e: any) { alert(e.message); }
  }

  const displayItems: Array<{ id: string; title: string; content: string; category: string; tags?: string[] | string | null; score?: number }> =
    searchResults
      ? searchResults.map(r => ({ ...r, tags: r.tags }))
      : entries.map(e => ({ ...e, tags: e.tags }));

  const selected = displayItems.find(i => i.id === selectedId);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">← 首页</Link>
            <h1 className="text-lg font-semibold text-gray-900">知识库</h1>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowUpload(true)}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg font-medium hover:bg-green-700">
              📊 上传 ROI Excel
            </button>
            <button onClick={() => setShowAdd(true)}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">
              + 添加知识
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* Search bar */}
        <div className="flex gap-3 mb-6">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="语义搜索知识库..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              className="w-full px-4 py-2.5 pr-20 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            />
            <button onClick={handleSearch} disabled={searching}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 text-xs bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50">
              {searching ? "搜索中..." : "搜索"}
            </button>
          </div>
          {searchResults && (
            <button onClick={() => { setSearchResults(null); setSearchQuery(""); }}
              className="px-3 py-2 text-sm text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50">
              清除
            </button>
          )}
        </div>

        {/* Category tabs */}
        <div className="flex gap-2 mb-6">
          {CATEGORIES.map(cat => (
            <button key={cat.id} onClick={() => { setCategory(cat.id); setSelectedId(null); }}
              className={`px-4 py-2 text-sm rounded-lg transition ${
                category === cat.id
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}>
              {cat.icon} {cat.label}
            </button>
          ))}
        </div>

        {searchResults && (
          <p className="text-sm text-gray-500 mb-4">
            搜索 "{searchQuery}" 找到 {searchResults.length} 条结果
          </p>
        )}

        {/* Content: list + detail */}
        <div className="flex gap-6">
          {/* List */}
          <div className="w-80 flex-shrink-0 space-y-2">
            {loading ? (
              <div className="text-center text-gray-400 py-8 text-sm">加载中...</div>
            ) : displayItems.length === 0 ? (
              <div className="text-center text-gray-400 py-8 text-sm">暂无数据</div>
            ) : (
              displayItems.map(item => {
                const catInfo = CATEGORIES.find(c => c.id === item.category);
                return (
                  <button key={item.id} onClick={() => setSelectedId(item.id)}
                    className={`w-full text-left p-3 rounded-lg border transition ${
                      selectedId === item.id ? "border-indigo-300 bg-indigo-50" : "border-gray-200 bg-white hover:bg-gray-50"
                    }`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">{item.content.substring(0, 80)}...</p>
                      </div>
                      <span className="text-base flex-shrink-0">{catInfo?.icon || "📄"}</span>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-400">{catInfo?.label || item.category}</span>
                      {"score" in item && item.score !== undefined && (
                        <span className="text-xs px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded">
                          {(item.score * 100).toFixed(0)}% 匹配
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Detail */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6">
            {selected ? (
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600">
                    {CATEGORIES.find(c => c.id === selected.category)?.label || selected.category}
                  </span>
                  {"score" in selected && selected.score !== undefined && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-600">
                      匹配度 {(selected.score * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-semibold text-gray-900 mt-2 mb-4">{selected.title}</h2>
                <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {selected.content}
                </div>
                {selected.tags && (
                  <div className="flex flex-wrap gap-1.5 mt-6 pt-4 border-t border-gray-100">
                    {(typeof selected.tags === "string" ? selected.tags.split(",") : selected.tags)
                      .filter(Boolean)
                      .map((tag: string, i: number) => (
                        <span key={i} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">{tag}</span>
                      ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-400 py-16">
                <p className="text-sm">选择左侧条目查看详情</p>
                <p className="text-xs mt-1">或使用搜索栏进行语义检索</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Add knowledge modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
            <h3 className="text-lg font-semibold mb-4">添加知识条目</h3>
            <div className="space-y-3">
              <select value={addForm.category} onChange={e => setAddForm({ ...addForm, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none">
                <option value="automation_case">自动化案例</option>
                <option value="cost_model">成本模型</option>
                <option value="logistics_case">物流案例</option>
              </select>
              <input placeholder="标题" value={addForm.title}
                onChange={e => setAddForm({ ...addForm, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none" />
              <textarea placeholder="内容..." value={addForm.content} rows={8}
                onChange={e => setAddForm({ ...addForm, content: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none resize-vertical" />
              <input placeholder="标签 (逗号分隔, 如: AGV,电商,拣选)" value={addForm.tags}
                onChange={e => setAddForm({ ...addForm, tags: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none" />
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">取消</button>
              <button onClick={handleAdd}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">添加</button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Excel Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
            <h3 className="text-lg font-semibold mb-2">上传 ROI Excel 文件</h3>
            <p className="text-xs text-gray-500 mb-4">
              支持包含 List/Summary 工作表的 ROI 模型 Excel。系统会自动提取每个设备的投资、IRR、NPV、回本周期等数据并转为知识条目。
            </p>
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">客户名称</label>
                <input
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  value={uploadForm.client_name}
                  onChange={e => setUploadForm({ ...uploadForm, client_name: e.target.value })}
                  placeholder="例：上海迪士尼"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">项目名称</label>
                <input
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  value={uploadForm.project_name}
                  onChange={e => setUploadForm({ ...uploadForm, project_name: e.target.value })}
                  placeholder="例：迪士尼仓储自动化升级"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">选择 Excel 文件</label>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) handleExcelUpload(f);
                  }}
                  disabled={uploading}
                  className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 file:font-medium hover:file:bg-indigo-100"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setShowUpload(false); setUploadForm({ project_name: "", client_name: "" }); }}
                disabled={uploading}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
              >
                {uploading ? "上传中..." : "取消"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

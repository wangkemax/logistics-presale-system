"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { projects as api, type Project } from "@/lib/api";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  created: { label: "已创建", color: "bg-gray-100 text-gray-700" },
  in_progress: { label: "进行中", color: "bg-blue-100 text-blue-700" },
  completed: { label: "已完成", color: "bg-green-100 text-green-700" },
  review_needed: { label: "待审核", color: "bg-orange-100 text-orange-700" },
  failed: { label: "失败", color: "bg-red-100 text-red-700" },
  archived: { label: "已归档", color: "bg-gray-100 text-gray-500" },
};

export default function DashboardPage() {
  const [projectList, setProjectList] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", client_name: "", industry: "", description: "" });

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const data = await api.list();
      setProjectList(data);
    } catch {
      // Not logged in or error
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!form.name.trim()) return;
    try {
      await api.create(form);
      setShowCreate(false);
      setForm({ name: "", client_name: "", industry: "", description: "" });
      loadProjects();
    } catch (e: any) {
      alert(e.message);
    }
  }

  const stats = {
    total: projectList.length,
    active: projectList.filter((p) => p.status === "in_progress").length,
    completed: projectList.filter((p) => p.status === "completed").length,
    review: projectList.filter((p) => p.status === "review_needed").length,
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">物流售前 AI 系统</h1>
            <p className="text-sm text-gray-500 mt-0.5">Logistics Presale Solution Platform</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/knowledge"
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              📚 知识库
            </Link>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
            >
              + 新建项目
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: "全部项目", value: stats.total, color: "text-gray-900" },
            { label: "进行中", value: stats.active, color: "text-blue-600" },
            { label: "已完成", value: stats.completed, color: "text-green-600" },
            { label: "待审核", value: stats.review, color: "text-orange-600" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm text-gray-500">{s.label}</p>
              <p className={`text-2xl font-semibold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Project List */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-base font-medium text-gray-900">项目列表</h2>
          </div>

          {loading ? (
            <div className="px-6 py-12 text-center text-gray-400">加载中...</div>
          ) : projectList.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-gray-400 mb-4">暂无项目，点击上方按钮创建第一个项目</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {projectList.map((project) => {
                const st = STATUS_MAP[project.status] || STATUS_MAP.created;
                const completedStages = project.stages?.filter((s: any) => s.status === "completed").length || 0;
                return (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{project.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {project.client_name || "未指定客户"} · {project.industry || "未指定行业"}
                        {project.description && <span className="ml-2 text-gray-400">— {project.description.slice(0, 40)}</span>}
                      </p>
                    </div>
                    <div className="flex items-center gap-4 ml-4">
                      {completedStages > 0 && (
                        <span className="text-xs text-gray-400">{completedStages}/12 阶段</span>
                      )}
                      <span className={`text-xs px-2.5 py-1 rounded-full ${st.color}`}>{st.label}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(project.created_at).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Create Project Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">新建售前项目</h3>

            {/* Template quick-pick */}
            <div className="mb-4">
              <label className="block text-sm text-gray-600 mb-2">快速选择行业模板</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "ecommerce_warehouse", icon: "📦", label: "电商仓储", industry: "电商" },
                  { id: "cold_chain", icon: "❄️", label: "冷链仓储", industry: "冷链" },
                  { id: "auto_parts", icon: "🚗", label: "汽车备件", industry: "汽车" },
                  { id: "pharma", icon: "💊", label: "医药物流", industry: "医药" },
                  { id: "fmcg", icon: "🏪", label: "快消分拨", industry: "快消" },
                  { id: "manufacturing", icon: "🏭", label: "制造业", industry: "制造" },
                ].map(t => (
                  <button key={t.id} type="button"
                    onClick={() => setForm({ ...form, industry: t.industry })}
                    className={`p-2 rounded-lg border text-sm text-left transition ${
                      form.industry === t.industry
                        ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                        : "border-gray-200 hover:bg-gray-50 text-gray-600"
                    }`}>
                    <span className="text-base mr-1">{t.icon}</span> {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">项目名称 *</label>
                <input
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="例：XX 公司仓储物流项目"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">客户名称</label>
                  <input
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                    value={form.client_name}
                    onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">行业</label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                    value={form.industry}
                    onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  >
                    <option value="">选择行业</option>
                    <option value="电商">电商</option>
                    <option value="快消">快消</option>
                    <option value="医药">医药</option>
                    <option value="冷链">冷链</option>
                    <option value="汽车">汽车</option>
                    <option value="电子">电子</option>
                    <option value="零售">零售</option>
                    <option value="制造">制造</option>
                    <option value="其他">其他</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">项目描述</label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none"
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
              >
                创建项目
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

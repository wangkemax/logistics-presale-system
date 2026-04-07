"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { projects as pApi, type Project, type Stage } from "@/lib/api";

export default function SolutionWorkbenchPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [activeView, setActiveView] = useState<"overview" | "warehouse" | "operations" | "technology" | "staffing">("overview");

  useEffect(() => {
    Promise.all([pApi.get(id), pApi.getStages(id)]).then(([p, s]) => {
      setProject(p);
      setStages(s);
    });
  }, [id]);

  const getStageData = (num: number) => {
    const stage = stages.find(s => s.stage_number === num);
    return stage?.output_data || {};
  };

  const solution = getStageData(5);
  const automation = getStageData(6);
  const requirements = getStageData(1);
  const dataAnalysis = getStageData(3);
  const costModel = getStageData(8);

  const warehouse = solution.warehouse_design || {};
  const operations = solution.operations_design || {};
  const technology = solution.technology || {};
  const staffing = solution.staffing || {};
  const performance = solution.performance || {};

  const VIEWS = [
    { key: "overview", label: "方案总览", icon: "📋" },
    { key: "warehouse", label: "仓库设计", icon: "🏗️" },
    { key: "operations", label: "运营流程", icon: "⚙️" },
    { key: "technology", label: "技术方案", icon: "💻" },
    { key: "staffing", label: "人员配置", icon: "👥" },
  ] as const;

  if (!project) return <div className="flex items-center justify-center min-h-screen text-gray-400">加载中...</div>;

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3 mb-2">
          <Link href={`/projects/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← 项目详情</Link>
        </div>
        <h1 className="text-lg font-semibold text-gray-900">方案设计工作台</h1>
        <p className="text-sm text-gray-500">{project.name}</p>
      </header>

      <div className="px-6 py-6 max-w-7xl mx-auto">
        {/* View tabs */}
        <div className="flex gap-2 mb-6">
          {VIEWS.map(v => (
            <button key={v.key} onClick={() => setActiveView(v.key)}
              className={`px-4 py-2 text-sm rounded-lg transition ${
                activeView === v.key ? "bg-indigo-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}>{v.icon} {v.label}</button>
          ))}
        </div>

        {/* Overview */}
        {activeView === "overview" && (
          <div className="space-y-6">
            {solution.executive_summary && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">执行摘要</h2>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{solution.executive_summary}</p>
              </div>
            )}

            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "仓库面积", value: warehouse.total_area_sqm ? `${warehouse.total_area_sqm.toLocaleString()} ㎡` : "—", icon: "📐" },
                { label: "人员编制", value: staffing.total_headcount || "—", icon: "👥" },
                { label: "日吞吐量", value: performance.daily_throughput ? `${performance.daily_throughput.toLocaleString()} 单` : "—", icon: "📦" },
                { label: "准确率目标", value: performance.accuracy_target || "—", icon: "🎯" },
              ].map(kpi => (
                <div key={kpi.label} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">{kpi.icon}</span>
                    <span className="text-xs text-gray-500">{kpi.label}</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900">{kpi.value}</p>
                </div>
              ))}
            </div>

            {/* Automation summary */}
            {automation.recommendations && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  自动化推荐 <span className="text-sm font-normal text-gray-400">({automation.automation_level})</span>
                </h2>
                <div className="grid grid-cols-2 gap-3">
                  {(automation.recommendations || []).slice(0, 6).map((rec: any, i: number) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-900">{rec.technology}</span>
                        <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded">{rec.suitability_score}/10</span>
                      </div>
                      <p className="text-xs text-gray-500">{rec.application_area}</p>
                      <div className="flex gap-4 mt-2 text-xs text-gray-500">
                        <span>投资 ¥{((rec.estimated_cost_cny || 0) / 10000).toFixed(0)}万</span>
                        <span>ROI {rec.roi_percent || 0}%</span>
                        <span>回本 {rec.payback_months || 0}月</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Warehouse Design */}
        {activeView === "warehouse" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">仓库布局</h2>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-sm text-gray-500 mb-1">总面积</p>
                  <p className="text-2xl font-bold text-gray-900">{warehouse.total_area_sqm?.toLocaleString() || "—"} ㎡</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 mb-1">流程设计</p>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{warehouse.flow_design || "未设计"}</p>
                </div>
              </div>
            </div>

            {warehouse.zones && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-4">功能分区</h2>
                <div className="grid grid-cols-3 gap-3">
                  {(Array.isArray(warehouse.zones) ? warehouse.zones : []).map((zone: any, i: number) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                      <p className="text-sm font-medium text-gray-900">{typeof zone === "string" ? zone : zone.name || zone.zone || `Zone ${i+1}`}</p>
                      {typeof zone === "object" && zone.area_sqm && (
                        <p className="text-xs text-gray-500 mt-1">{zone.area_sqm} ㎡</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {warehouse.storage_systems && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-4">存储系统</h2>
                <div className="space-y-2">
                  {(Array.isArray(warehouse.storage_systems) ? warehouse.storage_systems : []).map((sys: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <span className="text-lg">🗄️</span>
                      <span className="text-sm text-gray-700">{typeof sys === "string" ? sys : JSON.stringify(sys)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Operations */}
        {activeView === "operations" && (
          <div className="space-y-6">
            {["inbound", "storage", "picking", "packing_shipping", "returns"].map(key => {
              const section = operations[key];
              if (!section) return null;
              const labels: Record<string, string> = { inbound: "入库流程", storage: "存储策略", picking: "拣选流程", packing_shipping: "包装发运", returns: "退货处理" };
              const icons: Record<string, string> = { inbound: "📥", storage: "🗃️", picking: "🛒", packing_shipping: "📤", returns: "↩️" };
              return (
                <div key={key} className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="text-base font-semibold text-gray-900 mb-3">{icons[key]} {labels[key]}</h2>
                  {typeof section === "string" ? (
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{section}</p>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(section).map(([k, v]) => (
                        <div key={k} className="flex gap-3 text-sm">
                          <span className="text-gray-500 min-w-[100px]">{k}:</span>
                          <span className="text-gray-900">{typeof v === "string" ? v : JSON.stringify(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Technology */}
        {activeView === "technology" && (
          <div className="space-y-6">
            {technology.wms && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">WMS 系统</h2>
                <div className="text-sm text-gray-700">
                  {typeof technology.wms === "string" ? technology.wms : (
                    <div className="space-y-1">
                      {Object.entries(technology.wms).map(([k, v]) => (
                        <div key={k}><span className="text-gray-500">{k}:</span> {String(v)}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {technology.automation && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">自动化设备</h2>
                <div className="grid grid-cols-2 gap-2">
                  {(Array.isArray(technology.automation) ? technology.automation : []).map((item: any, i: number) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                      {typeof item === "string" ? item : JSON.stringify(item)}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {technology.integrations && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">系统集成</h2>
                <div className="space-y-2">
                  {(Array.isArray(technology.integrations) ? technology.integrations : []).map((item: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                      <span className="text-indigo-400">→</span>
                      {typeof item === "string" ? item : JSON.stringify(item)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Staffing */}
        {activeView === "staffing" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">人员配置</h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-indigo-50 rounded-lg text-center">
                  <p className="text-3xl font-bold text-indigo-700">{staffing.total_headcount || "—"}</p>
                  <p className="text-xs text-indigo-500 mt-1">总人数</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <p className="text-lg font-semibold text-gray-900">{staffing.shift_model || "—"}</p>
                  <p className="text-xs text-gray-500 mt-1">班次模式</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <p className="text-lg font-semibold text-gray-900">{performance.avg_lead_time_hours ? `${performance.avg_lead_time_hours}h` : "—"}</p>
                  <p className="text-xs text-gray-500 mt-1">平均交货时间</p>
                </div>
              </div>

              {staffing.by_function && typeof staffing.by_function === "object" && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">按职能分配</h3>
                  <div className="space-y-2">
                    {Object.entries(staffing.by_function).map(([role, count]) => (
                      <div key={role} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm text-gray-700">{role}</span>
                        <span className="text-sm font-semibold text-gray-900">{String(count)} 人</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!solution.executive_summary && !warehouse.total_area_sqm && (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
            <p className="text-3xl mb-3">🏗️</p>
            <p className="text-gray-500 text-sm">运行 Pipeline 完成 Stage 5 (方案设计) 后可查看</p>
          </div>
        )}
      </div>
    </div>
  );
}

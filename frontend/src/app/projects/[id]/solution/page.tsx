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

  // Smart renderer for objects — shows key:value pairs nicely instead of raw JSON
  function renderValue(val: any): string {
    if (val === null || val === undefined) return "—";
    if (typeof val === "string") return val;
    if (typeof val === "number") return val.toLocaleString();
    if (typeof val === "boolean") return val ? "是" : "否";
    if (Array.isArray(val)) return val.map(v => typeof v === "string" ? v : renderValue(v)).join(", ");
    return String(val);
  }

  function ObjectCard({ data, icon }: { data: any; icon?: string }) {
    if (typeof data === "string") return <span className="text-sm text-gray-700">{data}</span>;
    if (typeof data !== "object" || !data) return null;
    const LABELS: Record<string, string> = {
      type: "类型", name: "名称", capacity: "容量", description: "描述",
      height: "高度", coverage: "覆盖区域", roi_months: "回本周期(月)",
      length_meters: "长度(米)", strategy: "策略", methods: "方法",
      productivity: "产能", accuracy_target: "准确率目标",
      packing_strategy: "包装策略", shipping_methods: "运输方式",
      cut_off_times: "截单时间", area_sqm: "面积(㎡)", zone: "区域",
      application_area: "应用场景", suitability_score: "适配评分",
      estimated_cost_cny: "投资估算", annual_savings_cny: "年节省",
      roi_percent: "ROI", payback_months: "回本(月)", technology: "技术",
    };
    return (
      <div className="space-y-1">
        {Object.entries(data).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
          <div key={k} className="flex gap-2 text-sm">
            <span className="text-gray-500 min-w-[80px]">{LABELS[k] || k}:</span>
            <span className="text-gray-900">{renderValue(v)}</span>
          </div>
        ))}
      </div>
    );
  }

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

  // Try both English and Chinese field names since LLM output varies
  const warehouse = solution.warehouse_design || solution.仓库设计 || solution.warehouse || solution.仓储设计 || {};
  const operations = solution.operations_design || solution.运营设计 || solution.operations || solution.运营流程 || {};
  const technology = solution.technology || solution.技术方案 || solution.it_system || solution.IT方案 || {};
  const staffing = solution.staffing || solution.人员配置 || solution.team || solution.团队 || {};
  const performance = solution.performance || solution.绩效指标 || solution.kpi || solution.KPI || {};

  // Helper: get value trying multiple key names
  const getField = (obj: any, ...keys: string[]) => {
    if (!obj || typeof obj !== "object") return undefined;
    for (const k of keys) {
      if (obj[k] !== undefined) return obj[k];
    }
    return undefined;
  };

  const warehouseArea = getField(warehouse, "total_area_sqm", "总面积平米", "总面积", "面积", "area");
  const totalHeadcount = getField(staffing, "total_headcount", "总人数", "人数", "headcount");
  const dailyThroughput = getField(performance, "daily_throughput", "日吞吐量", "吞吐量", "throughput");
  const accuracyTarget = getField(performance, "accuracy_target", "准确率目标", "准确率", "accuracy");

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
            {(solution.executive_summary || solution.执行摘要) && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">执行摘要</h2>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{solution.executive_summary || solution.执行摘要}</p>
              </div>
            )}

            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "仓库面积", value: (warehouse.total_area_sqm || warehouse.总面积平米 || warehouse.面积) ? `${Number(warehouse.total_area_sqm || warehouse.总面积平米 || warehouse.面积).toLocaleString()} ㎡` : "—", icon: "📐" },
                { label: "人员编制", value: staffing.total_headcount || staffing.总人数 || staffing.人数 || "—", icon: "👥" },
                { label: "日吞吐量", value: (performance.daily_throughput || performance.日吞吐量) ? `${Number(performance.daily_throughput || performance.日吞吐量).toLocaleString()} 单` : "—", icon: "📦" },
                { label: "准确率目标", value: performance.accuracy_target || performance.准确率目标 || performance.准确率 || "—", icon: "🎯" },
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
                <div className="space-y-3">
                  {(Array.isArray(warehouse.storage_systems) ? warehouse.storage_systems : []).map((sys: any, i: number) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="flex items-start gap-3">
                        <span className="text-lg mt-0.5">🗄️</span>
                        <div className="flex-1">
                          {typeof sys === "string" ? (
                            <p className="text-sm text-gray-700">{sys}</p>
                          ) : (
                            <>
                              <p className="text-sm font-medium text-gray-900 mb-1">{sys.type || sys.name || `System ${i+1}`}</p>
                              <ObjectCard data={sys} />
                            </>
                          )}
                        </div>
                      </div>
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
                      {Object.entries(section).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
                        <div key={k} className="flex gap-3 text-sm">
                          <span className="text-gray-500 min-w-[120px]">{k}:</span>
                          <span className="text-gray-900">{renderValue(v)}</span>
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
                    <ObjectCard data={technology.wms} />
                  )}
                </div>
              </div>
            )}

            {technology.automation && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-base font-semibold text-gray-900 mb-3">自动化设备</h2>
                <div className="grid grid-cols-2 gap-3">
                  {(Array.isArray(technology.automation) ? technology.automation : []).map((item: any, i: number) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                      {typeof item === "string" ? (
                        <p className="text-sm text-gray-700">{item}</p>
                      ) : (
                        <>
                          <p className="text-sm font-medium text-gray-900 mb-1">{item.type || item.name || `Device ${i+1}`}</p>
                          <ObjectCard data={item} />
                        </>
                      )}
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
                      {typeof item === "string" ? item : renderValue(item)}
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
        {!solution.executive_summary && !solution.执行摘要 && !warehouseArea && Object.keys(solution).filter(k => !k.startsWith("_")).length === 0 && (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
            <p className="text-3xl mb-3">🏗️</p>
            <p className="text-gray-500 text-sm">运行 Pipeline 完成 Stage 5 (方案设计) 后可查看</p>
          </div>
        )}
      </div>
    </div>
  );
}

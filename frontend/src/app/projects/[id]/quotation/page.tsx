"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { projects as pApi, quotations as qApi, type Project, type Quotation } from "@/lib/api";

interface CostParams {
  warehouseArea: number;
  monthlyRent: number;
  headcount: number;
  avgSalary: number;
  orderVolume: number;
  automationInvestment: number;
  wmsCost: number;
  consumablesPerOrder: number;
  marginPct: number;
  contractYears: number;
  discountRate: number;
  annualGrowth: number;
}

const DEFAULT_PARAMS: CostParams = {
  warehouseArea: 10000,
  monthlyRent: 35,
  headcount: 80,
  avgSalary: 6500,
  orderVolume: 5000,
  automationInvestment: 3000000,
  wmsCost: 500000,
  consumablesPerOrder: 1.5,
  marginPct: 15,
  contractYears: 5,
  discountRate: 8,
  annualGrowth: 5,
};

function computeFinancials(p: CostParams) {
  const annualRent = p.warehouseArea * p.monthlyRent * 12;
  const annualLabor = p.headcount * p.avgSalary * 13; // 13 months
  const annualConsumables = p.orderVolume * 260 * p.consumablesPerOrder; // 260 work days
  const annualUtilities = p.warehouseArea * 4 * 12;
  const annualWMS = p.wmsCost > 100000 ? p.wmsCost / p.contractYears : p.wmsCost;
  const annualOverhead = annualLabor * 0.08;

  const totalOpex = annualRent + annualLabor + annualConsumables + annualUtilities + annualWMS + annualOverhead;
  const totalCapex = p.automationInvestment + (p.wmsCost > 100000 ? p.wmsCost : 0);
  const annualPrice = totalOpex * (1 + p.marginPct / 100);
  const pricePerOrder = annualPrice / (p.orderVolume * 260);
  const pricePerSqm = annualRent / p.warehouseArea / 12 * (1 + p.marginPct / 100);

  // NPV calculation
  let npv = -totalCapex;
  const annualProfit = annualPrice - totalOpex;
  for (let y = 1; y <= p.contractYears; y++) {
    const growth = Math.pow(1 + p.annualGrowth / 100, y - 1);
    const cashflow = annualProfit * growth;
    npv += cashflow / Math.pow(1 + p.discountRate / 100, y);
  }

  const roi = totalCapex > 0 ? (annualProfit / totalCapex) * 100 : 0;
  const paybackMonths = totalCapex > 0 && annualProfit > 0 ? Math.ceil((totalCapex / annualProfit) * 12) : 0;

  // Simplified IRR (Newton's method, 5 iterations)
  let irr = 0.1;
  for (let iter = 0; iter < 20; iter++) {
    let fv = -totalCapex;
    let dfv = 0;
    for (let y = 1; y <= p.contractYears; y++) {
      const cf = annualProfit * Math.pow(1 + p.annualGrowth / 100, y - 1);
      fv += cf / Math.pow(1 + irr, y);
      dfv -= y * cf / Math.pow(1 + irr, y + 1);
    }
    if (Math.abs(dfv) < 1e-10) break;
    irr = irr - fv / dfv;
    if (irr < -0.99) { irr = 0; break; }
  }

  return {
    breakdown: {
      rent: annualRent,
      labor: annualLabor,
      consumables: annualConsumables,
      utilities: annualUtilities,
      wms: annualWMS,
      overhead: annualOverhead,
    },
    totalOpex,
    totalCapex,
    annualPrice,
    pricePerOrder,
    pricePerSqm,
    roi,
    irr: irr * 100,
    npv,
    paybackMonths,
    annualProfit,
  };
}

function Slider({ label, value, onChange, min, max, step, unit, format }: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; unit: string;
  format?: (v: number) => string;
}) {
  const display = format ? format(value) : `${value.toLocaleString()} ${unit}`;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-indigo-600" />
    </div>
  );
}

function KPI({ label, value, sub, color = "text-gray-900" }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-bold mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function QuotationWorkbenchPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [params, setParams] = useState<CostParams>(DEFAULT_PARAMS);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [dataSource, setDataSource] = useState<"default" | "pipeline">("default");

  // Helper: get field with multiple key fallbacks
  const g = (obj: any, ...keys: string[]) => {
    if (!obj || typeof obj !== "object") return undefined;
    for (const k of keys) {
      if (obj[k] !== undefined) return obj[k];
    }
    return undefined;
  };

  useEffect(() => {
    Promise.all([pApi.get(id), pApi.getStages(id)]).then(([p, stages]) => {
      setProject(p);

      // Extract data from Stage 5 (Solution) and Stage 8 (Cost Model)
      const s5 = stages.find(s => s.stage_number === 5 && s.status === "completed");
      const s8 = stages.find(s => s.stage_number === 8 && s.status === "completed");

      if (!s5?.output_data && !s8?.output_data) return;

      const d5 = s5?.output_data || {};
      const d8 = s8?.output_data || {};

      const warehouse = g(d5, "warehouse_design", "仓库设计") || {};
      const staffing = g(d5, "staffing", "人员配置") || {};
      const costBreakdown = g(d8, "cost_breakdown", "成本分解") || {};
      const pricing = g(d8, "pricing", "定价模型", "报价") || {};
      const fi = g(d8, "financial_indicators", "财务指标") || {};

      // Extract area
      const area = Number(g(warehouse, "total_area_sqm", "总面积平方米", "总面积") || 0);
      // Extract headcount
      const hc = Number(g(staffing, "total_headcount", "总人数") || 0);
      // Extract labor cost to calculate avg salary
      const laborCost = g(costBreakdown, "labor_cost", "人力成本") || {};
      const laborY1 = Number(g(laborCost, "year1", "第一年") || 0);
      const avgSal = hc > 0 && laborY1 > 0 ? Math.round(laborY1 / hc / 13) : 0;
      // Extract rent from cost breakdown
      const rentCost = g(costBreakdown, "rent_cost", "场地成本", "租金") || {};
      const rentY1 = Number(g(rentCost, "year1", "第一年") || 0);
      const monthRent = area > 0 && rentY1 > 0 ? Math.round(rentY1 / area / 12) : 0;
      // Extract automation investment
      const equipCost = g(costBreakdown, "equipment_cost", "设备成本") || {};
      const autoInvest = Number(g(equipCost, "year1", "第一年", "total", "总额") || g(d8, "total_automation_investment", "总自动化投资") || 0);
      // Extract WMS/IT cost
      const techCost = g(costBreakdown, "technology_cost", "技术成本", "IT成本") || {};
      const wmsCostVal = Number(g(techCost, "year1", "第一年") || 0);
      // Extract margin
      const marginVal = Number(g(pricing, "target_margin_pct", "目标利润率") || 0);
      // Extract daily order volume from performance
      const perf = g(d5, "performance", "绩效指标") || {};
      const dailyVol = Number(g(perf, "daily_throughput", "日处理能力", "日吞吐量") || 0);

      // Build params from pipeline data, falling back to defaults
      const pipelineParams: CostParams = {
        warehouseArea: area || DEFAULT_PARAMS.warehouseArea,
        monthlyRent: monthRent || DEFAULT_PARAMS.monthlyRent,
        headcount: hc || DEFAULT_PARAMS.headcount,
        avgSalary: avgSal || DEFAULT_PARAMS.avgSalary,
        orderVolume: dailyVol || DEFAULT_PARAMS.orderVolume,
        automationInvestment: autoInvest || DEFAULT_PARAMS.automationInvestment,
        wmsCost: wmsCostVal || DEFAULT_PARAMS.wmsCost,
        consumablesPerOrder: DEFAULT_PARAMS.consumablesPerOrder,
        marginPct: marginVal > 1 ? marginVal : marginVal > 0 ? marginVal * 100 : DEFAULT_PARAMS.marginPct,
        contractYears: DEFAULT_PARAMS.contractYears,
        discountRate: DEFAULT_PARAMS.discountRate,
        annualGrowth: DEFAULT_PARAMS.annualGrowth,
      };

      setParams(pipelineParams);
      setDataSource("pipeline");
    }).catch(() => {});
  }, [id]);

  const fin = useMemo(() => computeFinancials(params), [params]);

  function updateParam(key: keyof CostParams, value: number) {
    setParams(prev => ({ ...prev, [key]: value }));
  }

  async function handleSaveQuotation() {
    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${API}/api/v1/projects/${id}/quotations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          scheme_name: "自定义报价",
          cost_breakdown: {
            params,
            computed: fin,
          },
        }),
      });
      setToast("报价已保存");
      setTimeout(() => setToast(""), 3000);
    } catch { setToast("保存失败"); }
    finally { setSaving(false); }
  }

  const fmt = (v: number) => `¥${(v / 10000).toFixed(1)}万`;

  return (
    <div className="min-h-screen">
      {toast && (
        <div className="fixed top-4 right-4 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg">{toast}</div>
      )}

      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3 mb-2">
          <Link href={`/projects/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← 项目详情</Link>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">报价计算工作台</h1>
            <p className="text-sm text-gray-500">
              {project?.name || ""} · 拖动参数实时联动
              {dataSource === "pipeline" && (
                <span className="ml-2 text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">已从 Pipeline 加载</span>
              )}
            </p>
          </div>
          <button onClick={handleSaveQuotation} disabled={saving}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50">
            {saving ? "保存中..." : "保存为报价方案"}
          </button>
        </div>
      </header>

      <div className="px-6 py-6 max-w-7xl mx-auto">
        {/* KPI Row */}
        <div className="grid grid-cols-6 gap-3 mb-6">
          <KPI label="年度报价" value={fmt(fin.annualPrice)} color="text-indigo-700" />
          <KPI label="单价/单" value={`¥${fin.pricePerOrder.toFixed(2)}`} />
          <KPI label="ROI" value={`${fin.roi.toFixed(1)}%`} color={fin.roi > 15 ? "text-green-600" : "text-orange-600"} />
          <KPI label="IRR" value={`${fin.irr.toFixed(1)}%`} color={fin.irr > 10 ? "text-green-600" : "text-orange-600"} />
          <KPI label="NPV" value={fmt(fin.npv)} color={fin.npv > 0 ? "text-green-600" : "text-red-600"} />
          <KPI label="回本" value={`${fin.paybackMonths}个月`} color={fin.paybackMonths < 24 ? "text-green-600" : "text-orange-600"} />
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* Left: Parameters */}
          <div className="col-span-1 space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">场地参数</h3>
              <Slider label="仓库面积" value={params.warehouseArea} onChange={v => updateParam("warehouseArea", v)}
                min={1000} max={100000} step={1000} unit="㎡" />
              <Slider label="月租单价" value={params.monthlyRent} onChange={v => updateParam("monthlyRent", v)}
                min={10} max={80} step={1} unit="元/㎡/月" />
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">人力参数</h3>
              <Slider label="总人数" value={params.headcount} onChange={v => updateParam("headcount", v)}
                min={10} max={500} step={5} unit="人" />
              <Slider label="月均工资" value={params.avgSalary} onChange={v => updateParam("avgSalary", v)}
                min={4000} max={15000} step={500} unit="元/月" />
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">业务参数</h3>
              <Slider label="日均订单" value={params.orderVolume} onChange={v => updateParam("orderVolume", v)}
                min={500} max={100000} step={500} unit="单/天" />
              <Slider label="耗材成本" value={params.consumablesPerOrder} onChange={v => updateParam("consumablesPerOrder", v)}
                min={0.5} max={5} step={0.1} unit="元/单" />
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">投资参数</h3>
              <Slider label="自动化投资" value={params.automationInvestment} onChange={v => updateParam("automationInvestment", v)}
                min={0} max={50000000} step={500000} unit="" format={v => fmt(v)} />
              <Slider label="WMS 系统" value={params.wmsCost} onChange={v => updateParam("wmsCost", v)}
                min={20000} max={2000000} step={10000} unit="" format={v => fmt(v)} />
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">商务参数</h3>
              <Slider label="利润率" value={params.marginPct} onChange={v => updateParam("marginPct", v)}
                min={5} max={35} step={1} unit="%" />
              <Slider label="合同年限" value={params.contractYears} onChange={v => updateParam("contractYears", v)}
                min={1} max={10} step={1} unit="年" />
              <Slider label="年增长率" value={params.annualGrowth} onChange={v => updateParam("annualGrowth", v)}
                min={0} max={20} step={1} unit="%" />
              <Slider label="折现率" value={params.discountRate} onChange={v => updateParam("discountRate", v)}
                min={3} max={15} step={0.5} unit="%" />
            </div>
          </div>

          {/* Right: Results */}
          <div className="col-span-2 space-y-4">
            {/* Cost breakdown */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">年度成本分解</h3>
              <div className="space-y-2">
                {[
                  { label: "场地租金", value: fin.breakdown.rent, pct: fin.breakdown.rent / fin.totalOpex * 100 },
                  { label: "人力成本", value: fin.breakdown.labor, pct: fin.breakdown.labor / fin.totalOpex * 100 },
                  { label: "耗材包装", value: fin.breakdown.consumables, pct: fin.breakdown.consumables / fin.totalOpex * 100 },
                  { label: "水电物业", value: fin.breakdown.utilities, pct: fin.breakdown.utilities / fin.totalOpex * 100 },
                  { label: "信息系统", value: fin.breakdown.wms, pct: fin.breakdown.wms / fin.totalOpex * 100 },
                  { label: "管理费用", value: fin.breakdown.overhead, pct: fin.breakdown.overhead / fin.totalOpex * 100 },
                ].map(item => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{item.label}</span>
                      <span className="text-gray-900">{fmt(item.value)} <span className="text-gray-400 text-xs">({item.pct.toFixed(1)}%)</span></span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className="bg-indigo-400 h-2 rounded-full transition-all" style={{ width: `${Math.min(item.pct, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-4 pt-3 border-t border-gray-200 text-sm font-semibold">
                <span>年运营总成本 (OPEX)</span>
                <span className="text-gray-900">{fmt(fin.totalOpex)}</span>
              </div>
              <div className="flex justify-between mt-1 text-sm font-semibold">
                <span>总投资 (CAPEX)</span>
                <span className="text-gray-900">{fmt(fin.totalCapex)}</span>
              </div>
            </div>

            {/* Pricing */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">报价方案</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">每单操作费</p>
                  <p className="text-xl font-bold text-indigo-700 mt-1">¥{fin.pricePerOrder.toFixed(2)}</p>
                  <p className="text-[10px] text-gray-400">元/单</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">仓储费</p>
                  <p className="text-xl font-bold text-indigo-700 mt-1">¥{fin.pricePerSqm.toFixed(1)}</p>
                  <p className="text-[10px] text-gray-400">元/㎡/月</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-xs text-gray-500">年度总价</p>
                  <p className="text-xl font-bold text-indigo-700 mt-1">{fmt(fin.annualPrice)}</p>
                  <p className="text-[10px] text-gray-400">元/年</p>
                </div>
              </div>
            </div>

            {/* Multi-year projection */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">{params.contractYears} 年现金流预测</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 border-b border-gray-200">
                    <th className="py-2 text-left">年份</th>
                    <th className="py-2 text-right">收入</th>
                    <th className="py-2 text-right">成本</th>
                    <th className="py-2 text-right">利润</th>
                    <th className="py-2 text-right">累计利润</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: params.contractYears }, (_, y) => {
                    const growth = Math.pow(1 + params.annualGrowth / 100, y);
                    const rev = fin.annualPrice * growth;
                    const cost = fin.totalOpex * growth;
                    const profit = rev - cost;
                    const cumProfit = Array.from({ length: y + 1 }, (_, j) => {
                      const g = Math.pow(1 + params.annualGrowth / 100, j);
                      return (fin.annualPrice - fin.totalOpex) * g;
                    }).reduce((a, b) => a + b, 0) - fin.totalCapex;
                    return (
                      <tr key={y} className={y % 2 === 1 ? "bg-gray-50" : ""}>
                        <td className="py-2 text-gray-700">第 {y + 1} 年</td>
                        <td className="py-2 text-right text-gray-900">{fmt(rev)}</td>
                        <td className="py-2 text-right text-gray-900">{fmt(cost)}</td>
                        <td className="py-2 text-right text-green-600">{fmt(profit)}</td>
                        <td className={`py-2 text-right font-medium ${cumProfit >= 0 ? "text-green-600" : "text-red-600"}`}>
                          {fmt(cumProfit)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

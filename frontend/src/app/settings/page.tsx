"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [config, setConfig] = useState({
    llm_model: "claude-sonnet-4-20250514",
    agent_timeout: 10,
    max_retries: 2,
    cache_ttl: 24,
  });

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">系统设置</h1>
        <p className="text-sm text-gray-500 mt-0.5">配置 AI Agent 参数和系统行为</p>
      </header>

      <div className="max-w-2xl px-6 py-6 space-y-6">
        {/* LLM Configuration */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">AI 模型配置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">主模型</label>
              <select value={config.llm_model}
                onChange={e => setConfig({ ...config, llm_model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none">
                <option value="claude-sonnet-4-20250514">Claude Sonnet 4 (推荐)</option>
                <option value="claude-opus-4-6">Claude Opus 4.6 (最强)</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Agent 超时 (分钟)</label>
                <input type="number" value={config.agent_timeout}
                  onChange={e => setConfig({ ...config, agent_timeout: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">最大重试次数</label>
                <input type="number" value={config.max_retries}
                  onChange={e => setConfig({ ...config, max_retries: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none" />
              </div>
            </div>
          </div>
        </div>

        {/* Cache */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">缓存配置</h2>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Agent 缓存有效期 (小时)</label>
            <input type="number" value={config.cache_ttl}
              onChange={e => setConfig({ ...config, cache_ttl: Number(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none" />
            <p className="text-xs text-gray-400 mt-1">相同输入的 Agent 结果将在此时间内复用，避免重复调用 LLM</p>
          </div>
        </div>

        {/* Pipeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">流水线阶段</h2>
          <div className="space-y-2 text-sm">
            {[
              { n: 0, name: "项目假设", agent: "manual" },
              { n: 1, name: "招标文件解析", agent: "requirement_extractor" },
              { n: 2, name: "需求澄清", agent: "requirement_clarifier" },
              { n: 3, name: "数据分析", agent: "data_analyst" },
              { n: 4, name: "知识库检索", agent: "knowledge_base" },
              { n: 5, name: "方案设计", agent: "logistics_architect" },
              { n: 6, name: "自动化推荐", agent: "automation_solution" },
              { n: 7, name: "案例匹配", agent: "benchmark" },
              { n: 8, name: "成本建模", agent: "cost_model" },
              { n: 9, name: "风险评估", agent: "risk_compliance" },
              { n: 10, name: "标书撰写", agent: "tender_writer" },
              { n: 11, name: "QA 审核", agent: "qa_agent" },
            ].map(s => (
              <div key={s.n} className="flex items-center justify-between py-1.5 px-3 rounded hover:bg-gray-50">
                <span className="text-gray-700">Stage {s.n}: {s.name}</span>
                <span className="text-xs text-gray-400 font-mono">{s.agent}</span>
              </div>
            ))}
          </div>
        </div>

        <button className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
          保存设置
        </button>
      </div>
    </div>
  );
}

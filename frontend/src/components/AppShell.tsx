"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "项目总览", icon: "📊" },
  { href: "/analytics", label: "数据看板", icon: "📈" },
  { href: "/knowledge", label: "知识库", icon: "📚" },
  { href: "/settings", label: "系统设置", icon: "⚙️" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isProjectDetail = pathname.startsWith("/projects/");

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
        <div className="px-5 py-5 border-b border-gray-100">
          <Link href="/" className="block">
            <p className="text-sm font-semibold text-gray-900">物流售前 AI</p>
            <p className="text-[10px] text-gray-400 mt-0.5 tracking-wide">PRESALE SYSTEM</p>
          </Link>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(item => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${
                  active ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-600 hover:bg-gray-50"
                }`}>
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-5 py-4 border-t border-gray-100">
          <p className="text-[10px] text-gray-400">v0.3.0 · Phase 3</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 bg-gray-50">
        {children}
      </main>
    </div>
  );
}

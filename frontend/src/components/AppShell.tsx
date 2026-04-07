"use client";

import { useState } from "react";
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
  const [mobileOpen, setMobileOpen] = useState(false);

  const navContent = (
    <>
      <div className="px-5 py-5 border-b border-gray-100">
        <Link href="/" className="block" onClick={() => setMobileOpen(false)}>
          <p className="text-sm font-semibold text-gray-900">物流售前 AI</p>
          <p className="text-[10px] text-gray-400 mt-0.5 tracking-wide">PRESALE SYSTEM</p>
        </Link>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(item => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition ${
                active ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-600 hover:bg-gray-50"
              }`}>
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 border-t border-gray-100">
        <p className="text-[10px] text-gray-400">v0.4.0 · Phase 4</p>
      </div>
    </>
  );

  return (
    <div className="min-h-screen flex">
      {/* Desktop sidebar */}
      <aside className="hidden sm:flex w-56 bg-white border-r border-gray-200 flex-col flex-shrink-0">
        {navContent}
      </aside>

      {/* Mobile header bar */}
      <div className="sm:hidden fixed top-0 left-0 right-0 z-40 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <button onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1 text-gray-600 hover:bg-gray-100 rounded-lg">
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round"/>
          </svg>
        </button>
        <span className="text-sm font-semibold text-gray-900">物流售前 AI</span>
        <div className="w-8" />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <>
          <div className="sm:hidden fixed inset-0 bg-black/30 z-40" onClick={() => setMobileOpen(false)} />
          <aside className="sm:hidden fixed left-0 top-0 bottom-0 w-64 bg-white z-50 flex flex-col shadow-xl">
            {navContent}
          </aside>
        </>
      )}

      {/* Main content */}
      <main className="flex-1 min-w-0 bg-gray-50 sm:pt-0 pt-14">
        {children}
      </main>
    </div>
  );
}

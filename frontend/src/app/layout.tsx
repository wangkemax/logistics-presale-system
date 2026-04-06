import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "物流售前 AI 系统",
  description: "基于多 Agent 协同的物流售前解决方案及报价系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}

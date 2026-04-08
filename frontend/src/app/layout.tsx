import "./globals.css";
import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/AppShell";
import { ErrorBoundary } from "@/components/UIKit";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";

export const metadata: Metadata = {
  title: "物流售前 AI 系统",
  description: "基于多 Agent 协同的物流售前解决方案及报价系统",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "售前AI",
  },
  formatDetection: {
    telephone: false,
  },
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/icon-192.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#4f46e5",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
      </head>
      <body className="min-h-screen bg-gray-50">
        <ErrorBoundary>
          <AppShell>{children}</AppShell>
        </ErrorBoundary>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}

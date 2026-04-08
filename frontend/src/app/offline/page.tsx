"use client";

import { useEffect, useState } from "react";

export default function OfflinePage() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(navigator.onLine);

    const goOnline = () => setIsOnline(true);
    const goOffline = () => setIsOnline(false);

    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);

    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  if (isOnline) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <p className="text-3xl mb-3">✅</p>
          <p className="text-gray-600 text-sm">网络已恢复，正在重新加载...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-sm">
        <p className="text-5xl mb-4">📡</p>
        <h1 className="text-lg font-semibold text-gray-900 mb-2">网络已断开</h1>
        <p className="text-sm text-gray-500 mb-6">
          物流售前 AI 系统需要网络连接才能正常工作。请检查网络后重试。
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
        >
          重试连接
        </button>
      </div>
    </div>
  );
}

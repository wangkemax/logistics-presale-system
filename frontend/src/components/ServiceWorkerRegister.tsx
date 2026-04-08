"use client";

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker
        .register("/sw.js")
        .then((reg) => {
          console.log("[PWA] Service worker registered:", reg.scope);

          // Check for updates every 30 minutes
          setInterval(() => reg.update(), 30 * 60 * 1000);
        })
        .catch((err) => {
          console.log("[PWA] Service worker registration failed:", err);
        });
    }
  }, []);

  return null;
}

/**
 * useWebSocket — connects to the backend WebSocket for real-time pipeline updates.
 * Auto-reconnects on disconnect. Provides typed event callbacks.
 */
import { useEffect, useRef, useCallback, useState } from "react";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace("http", "ws");

export interface WSEvent {
  event: string;
  project_id: string;
  stage_number: number | null;
  data: Record<string, any>;
  timestamp: string;
}

interface UseWebSocketOptions {
  projectId: string;
  onStageStarted?: (stage: number, data: any) => void;
  onStageCompleted?: (stage: number, data: any) => void;
  onStageFailed?: (stage: number, data: any) => void;
  onPipelineCompleted?: (data: any) => void;
}

export function useWebSocket({
  projectId,
  onStageStarted,
  onStageCompleted,
  onStageFailed,
  onPipelineCompleted,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    const token = localStorage.getItem("token");
    if (!token || !projectId) return;

    const url = `${WS_BASE}/ws/${projectId}?token=${token}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      console.log("[WS] Connected:", projectId);
    };

    ws.onmessage = (evt) => {
      try {
        const msg: WSEvent = JSON.parse(evt.data);

        if (msg.event === "ping") {
          ws.send("pong");
          return;
        }

        switch (msg.event) {
          case "stage_started":
            onStageStarted?.(msg.stage_number!, msg.data);
            break;
          case "stage_completed":
            onStageCompleted?.(msg.stage_number!, msg.data);
            break;
          case "stage_failed":
            onStageFailed?.(msg.stage_number!, msg.data);
            break;
          case "pipeline_completed":
            onPipelineCompleted?.(msg.data);
            break;
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("[WS] Disconnected, reconnecting in 3s...");
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [projectId, onStageStarted, onStageCompleted, onStageFailed, onPipelineCompleted]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}

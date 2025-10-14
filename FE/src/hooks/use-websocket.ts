import { useEffect, useRef, useState, useCallback } from "react";
import { WS_URL } from "@/lib/api";

export type WebSocketMessage = {
  event: string;
  job_id: number;
  status: string;
  result?: any;
};

type WebSocketHook = {
  connected: boolean;
  message: WebSocketMessage | null;
  sendMessage: (msg: any) => void;
};

export function useWebSocket(onMessage?: (msg: WebSocketMessage) => void): WebSocketHook {
  const [connected, setConnected] = useState(false);
  const [message, setMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[WebSocket] Received:", data);
          setMessage(data);
          if (onMessage) {
            onMessage(data);
          }
        } catch (e) {
          console.error("[WebSocket] Failed to parse message:", e);
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
      };

      ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        setConnected(false);
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("[WebSocket] Attempting to reconnect...");
          connect();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("[WebSocket] Connection failed:", error);
      // Retry after 5 seconds if initial connection fails
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 5000);
    }
  }, [onMessage]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn("[WebSocket] Not connected, cannot send message");
    }
  }, []);

  return { connected, message, sendMessage };
}


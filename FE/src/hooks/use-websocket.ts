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

// --- Singleton connection across the app (one socket per tab) ---
let singletonWs: WebSocket | null = null;
let heartbeatTimer: any = null;
let reconnectTimer: any = null;
let closed = false;
let backoff = 1000; // start 1s
const listeners = new Set<(msg: WebSocketMessage) => void>();
let connectedFlag = false;
const subscribers = new Set<(state: boolean) => void>();

function notifyConnected(val: boolean) {
  connectedFlag = val;
  subscribers.forEach((fn) => { try { fn(val); } catch {} });
}

function ensureSocket() {
  if (singletonWs && (singletonWs.readyState === WebSocket.OPEN || singletonWs.readyState === WebSocket.CONNECTING)) {
    return;
  }
  try {
    const ws = new WebSocket(WS_URL);
    singletonWs = ws;
    ws.onopen = () => {
      notifyConnected(true);
      backoff = 1000;
      // Heartbeat every 25s
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      heartbeatTimer = setInterval(() => { try { ws.send(JSON.stringify({ type: "ping" })); } catch {} }, 25000);
    };
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        listeners.forEach((fn) => { try { fn(data); } catch {} });
      } catch {}
    };
    ws.onerror = () => { try { ws.close(); } catch {} };
    ws.onclose = () => {
      notifyConnected(false);
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      if (!closed) {
        const next = Math.min(backoff * 2, 30000);
        const jitter = Math.floor(Math.random() * 500);
        backoff = next;
        reconnectTimer = setTimeout(() => ensureSocket(), next + jitter);
      }
    };
  } catch {
    const next = Math.min(backoff * 2, 30000);
    backoff = next;
    reconnectTimer = setTimeout(() => ensureSocket(), next);
  }
}

export function useWebSocket(onMessage?: (msg: WebSocketMessage) => void): WebSocketHook {
  const [connected, setConnected] = useState<boolean>(connectedFlag);
  const [message, setMessage] = useState<WebSocketMessage | null>(null);
  const localListener = useRef<(msg: WebSocketMessage) => void>();

  useEffect(() => {
    // subscribe to connection state updates
    const s = (v: boolean) => setConnected(v);
    subscribers.add(s);
    // create the socket if needed
    ensureSocket();
    return () => { subscribers.delete(s); };
  }, []);

  useEffect(() => {
    localListener.current = (data: WebSocketMessage) => {
      setMessage(data);
      if (onMessage) { try { onMessage(data); } catch {} }
    };
    listeners.add(localListener.current);
    return () => { if (localListener.current) listeners.delete(localListener.current); };
  }, [onMessage]);

  useEffect(() => {
    return () => {
      // do not close global socket here; it is shared by the app
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const sendMessage = useCallback((msg: any) => {
    if (singletonWs && singletonWs.readyState === WebSocket.OPEN) {
      try { singletonWs.send(JSON.stringify(msg)); } catch {}
    } else {
      console.warn("[WebSocket] Not connected, cannot send message");
    }
  }, []);

  return { connected, message, sendMessage };
}


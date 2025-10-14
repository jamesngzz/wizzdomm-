import { ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Brain, Home, FileText, Upload, CheckCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { icon: FileText, label: "Quản lý đề thi", path: "/exams" },
    { icon: Upload, label: "Bài nộp", path: "/submissions" },
    { icon: CheckCircle, label: "Chấm bài", path: "/grading" },
  ];

  const [collapsed, setCollapsed] = useState(false);
  const [gradingTabs, setGradingTabs] = useState<Array<{ id: number; label?: string }>>([]);
  const [cropTabs, setCropTabs] = useState<Array<{ id: number; label?: string }>>([]);
  const [hydrated, setHydrated] = useState(false);
  const MAX_TABS = 10;

  // Helpers
  const persist = (key: string, value: unknown) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
  };

  const readPersist = (key: string): any => {
    try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : null; } catch { return null; }
  };

  const addTab = (
    which: "grading" | "crop",
    id: number,
    label?: string,
  ) => {
    if (!id || Number.isNaN(id)) return;
    const key = which === "grading" ? "sidebar:gradingTabs" : "sidebar:cropTabs";
    const current = readPersist(key);
    const base: Array<{ id: number; label?: string }> = Array.isArray(current)
      ? current.filter((t: any) => t && typeof t.id === "number")
      : (which === "grading" ? gradingTabs : cropTabs);
    if (base.some((t) => t.id === id)) return;
    let next = [...base, { id, label }];
    if (next.length > MAX_TABS) next = next.slice(-MAX_TABS);
    persist(key, next);
    if (which === "grading") setGradingTabs(next); else setCropTabs(next);
  };

  const updateTabLabel = (which: "grading" | "crop", id: number, label?: string) => {
    if (!id) return;
    if (which === "grading") {
      setGradingTabs((prev) => prev.map((t) => (t.id === id ? { ...t, label: label || t.label } : t)));
    } else {
      setCropTabs((prev) => prev.map((t) => (t.id === id ? { ...t, label: label || t.label } : t)));
    }
  };

  const closeTab = (which: "grading" | "crop", id: number) => {
    if (which === "grading") {
      setGradingTabs((prev) => prev.filter((t) => t.id !== id));
      if (location.pathname === "/grading") {
        const sp = new URLSearchParams(location.search);
        const cur = Number(sp.get("submissionId"));
        if (cur === id) navigate("/grading");
      }
    } else {
      setCropTabs((prev) => prev.filter((t) => t.id !== id));
      if (location.pathname === "/submissions/crop") {
        const sp = new URLSearchParams(location.search);
        const cur = Number(sp.get("submissionId"));
        if (cur === id) navigate("/submissions");
      }
    }
  };

  // Load persisted tabs on mount
  useEffect(() => {
    const g = readPersist("sidebar:gradingTabs");
    const c = readPersist("sidebar:cropTabs");
    if (Array.isArray(g)) setGradingTabs(g.filter((t: any) => t && typeof t.id === "number").slice(-MAX_TABS));
    if (Array.isArray(c)) setCropTabs(c.filter((t: any) => t && typeof t.id === "number").slice(-MAX_TABS));
    setHydrated(true);
  }, []);

  // Persist on change
  useEffect(() => { if (hydrated) persist("sidebar:gradingTabs", gradingTabs); }, [gradingTabs, hydrated]);
  useEffect(() => { if (hydrated) persist("sidebar:cropTabs", cropTabs); }, [cropTabs, hydrated]);

  // React to external storage updates (tabs added from Submissions buttons)
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === "sidebar:gradingTabs") {
        const g = readPersist("sidebar:gradingTabs");
        if (Array.isArray(g)) setGradingTabs(g.slice(-MAX_TABS));
      } else if (e.key === "sidebar:cropTabs") {
        const c = readPersist("sidebar:cropTabs");
        if (Array.isArray(c)) setCropTabs(c.slice(-MAX_TABS));
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  // On route change, auto-create tab if visiting grading/crop with submissionId
  useEffect(() => {
    const sp = new URLSearchParams(location.search);
    const sid = Number(sp.get("submissionId"));
    if (location.pathname === "/grading" && sid) addTab("grading", sid);
    if (location.pathname === "/submissions/crop" && sid) addTab("crop", sid);
  }, [location.key, location.pathname, location.search]);

  // Listen for label updates dispatched by pages
  useEffect(() => {
    const handlerG = (e: any) => {
      const id = Number(e?.detail?.id);
      const label = e?.detail?.label as string | undefined;
      if (id) updateTabLabel("grading", id, label);
    };
    const handlerC = (e: any) => {
      const id = Number(e?.detail?.id);
      const label = e?.detail?.label as string | undefined;
      if (id) updateTabLabel("crop", id, label);
    };
    const handlerAdd = (e: any) => {
      const which = e?.detail?.which as "grading" | "crop";
      const id = Number(e?.detail?.id);
      const label = e?.detail?.label as string | undefined;
      if ((which === "grading" || which === "crop") && id) addTab(which, id, label);
    };
    window.addEventListener("ta:update-grading-tab", handlerG as any);
    window.addEventListener("ta:update-crop-tab", handlerC as any);
    window.addEventListener("ta:add-tab", handlerAdd as any);
    return () => {
      window.removeEventListener("ta:update-grading-tab", handlerG as any);
      window.removeEventListener("ta:update-crop-tab", handlerC as any);
      window.removeEventListener("ta:add-tab", handlerAdd as any);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-full border-r border-border bg-card transition-[width] duration-200",
          collapsed ? "w-14" : "w-64"
        )}
      >
        <div className={cn("flex h-16 items-center gap-3 border-b border-border", collapsed ? "px-3" : "px-6")}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-primary">
            <Brain className="h-6 w-6 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="text-lg font-bold text-foreground">Wizzdom</h1>
              <p className="text-xs text-muted-foreground">Hệ thống chấm bài Toán AI</p>
            </div>
          )}
          <button
            aria-label="Toggle sidebar"
            className={cn("ml-auto inline-flex items-center justify-center rounded-md border px-2 py-1 text-muted-foreground hover:bg-muted", collapsed ? "" : "")}
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        <nav className={cn("space-y-1", collapsed ? "p-2" : "p-4")}
        >
          {!collapsed && (
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Điều hướng
            </p>
          )}
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const node = (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="h-5 w-5" />
                {!collapsed && item.label}
              </Link>
            );
            return (
              <div key={item.path} className="space-y-1">
                {node}
                {!collapsed && item.path === "/submissions" && cropTabs.length > 0 && (
                  <div className="ml-6 space-y-1">
                    {cropTabs.map((t) => {
                      const active = location.pathname === "/submissions/crop" && new URLSearchParams(location.search).get("submissionId") === String(t.id);
                      return (
                        <div key={`crop-${t.id}`} className={cn("flex items-center justify-between rounded px-2 py-1 text-sm", active ? "bg-primary/10 text-foreground" : "hover:bg-muted")}
                        >
                          <button
                            className="text-left flex-1 truncate"
                            onClick={() => navigate(`/submissions/crop?submissionId=${t.id}`)}
                            title={t.label || `#${t.id}`}
                          >
                            {t.label || `#${t.id}`}
                          </button>
                          <button className="text-xs text-muted-foreground hover:text-foreground" onClick={() => closeTab("crop", t.id)}>✕</button>
                        </div>
                      );
                    })}
                  </div>
                )}
                {!collapsed && item.path === "/grading" && gradingTabs.length > 0 && (
                  <div className="ml-6 space-y-1">
                    {gradingTabs.map((t) => {
                      const active = location.pathname === "/grading" && new URLSearchParams(location.search).get("submissionId") === String(t.id);
                      return (
                        <div key={`grading-${t.id}`} className={cn("flex items-center justify-between rounded px-2 py-1 text-sm", active ? "bg-primary/10 text-foreground" : "hover:bg-muted")}
                        >
                          <button
                            className="text-left flex-1 truncate"
                            onClick={() => navigate(`/grading?submissionId=${t.id}`)}
                            title={t.label || `#${t.id}`}
                          >
                            {t.label || `#${t.id}`}
                          </button>
                          <button className="text-xs text-muted-foreground hover:text-foreground" onClick={() => closeTab("grading", t.id)}>✕</button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="absolute bottom-4 left-4 right-4">
            <div className="rounded-lg border border-border bg-muted/50 p-4">
              <div className="mb-2 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
                <p className="text-xs font-medium text-foreground">Đang hoạt động</p>
              </div>
              <p className="text-xs text-muted-foreground">AI Vision Model sẵn sàng</p>
            </div>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className={cn("min-h-screen transition-[margin-left] duration-200", collapsed ? "ml-14" : "ml-64")}
      >
        <div className="p-2">{children}</div>
      </main>
    </div>
  );
};

export default Layout;

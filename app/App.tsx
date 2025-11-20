"use client";

import { useCallback, useState } from "react";
import { ChatKitPanel, type FactAction } from "@/components/ChatKitPanel";
import { useColorScheme } from "@/hooks/useColorScheme";

export default function App() {
  const { scheme, setScheme } = useColorScheme();
  const [isMinimized, setIsMinimized] = useState(false);

  const handleWidgetAction = useCallback(async (action: FactAction) => {
    if (process.env.NODE_ENV !== "production") {
      console.info("[ChatKitPanel] widget action", action);
    }
  }, []);

  const handleResponseEnd = useCallback(() => {
    if (process.env.NODE_ENV !== "production") {
      console.debug("[ChatKitPanel] response end");
    }
  }, []);

  return (
    <main
      className="relative min-h-screen bg-slate-100 dark:bg-slate-950"
      style={{
        backgroundImage: "url('/sfdc_image.jpg')",
        backgroundSize: "contain",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "center",
        backgroundColor: "#fff",
      }}
    >
      <div className="pointer-events-none fixed bottom-4 right-0 z-40 flex flex-col items-end">
        <div
          className={`pointer-events-auto transition duration-150 ${
            isMinimized ? "hidden" : "block"
          }`}
          aria-hidden={isMinimized}
          style={{ width: "clamp(320px, 50vw, 960px)" }}
        >
          <ChatKitPanel
            theme={scheme}
            onWidgetAction={handleWidgetAction}
            onResponseEnd={handleResponseEnd}
            onThemeRequest={setScheme}
            onToggleVisibility={() => setIsMinimized(true)}
          />
        </div>
      </div>
      <div
        className="pointer-events-none fixed z-50"
        style={{ top: "142px", right: "430px" }}
      >
        <button
          type="button"
          className="pointer-events-auto inline-flex h-[calc(2.1rem)] items-center justify-center rounded-full px-5 text-sm font-semibold text-white shadow-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
          style={{ backgroundColor: "#066afe" }}
          onClick={() => setIsMinimized((prev) => !prev)}
        >
          CIX Agent
        </button>
      </div>
    </main>
  );
}

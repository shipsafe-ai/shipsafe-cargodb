"use client";
import { useState } from "react";
import MemoryBrowser from "@/components/MemoryBrowser";
import VectorSimilarity from "@/components/VectorSimilarity";
import SchemaDriftPanel from "@/components/SchemaDriftPanel";
import PendingApprovals from "@/components/PendingApprovals";

type Tab = "memory" | "similarity" | "schema" | "pending";

const TABS: { id: Tab; label: string }[] = [
  { id: "memory", label: "Memory Browser" },
  { id: "similarity", label: "Vector Similarity" },
  { id: "schema", label: "Schema Drift" },
  { id: "pending", label: "Pending Approvals" },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("memory");

  return (
    <div className="min-h-screen bg-bg-base">
      {/* Header */}
      <header className="border-b border-border bg-bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="https://shipsafe-landing-o34wppiwiq-uc.a.run.app"
             className="text-xs font-mono text-muted hover:text-text-secondary transition-colors"
             style={{ textDecoration: 'none' }}>
            ← ShipSafe
          </a>
          <span className="text-muted" style={{ fontSize: 10 }}>·</span>
          <span className="text-cargo-accent font-mono text-lg font-semibold tracking-tight">
            CargoDB
          </span>
          <span className="text-muted text-sm font-mono">/ agent memory</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-cargo-accent" />
          <span className="text-xs font-mono text-text-secondary">
            Atlas Vector Search
          </span>
        </div>
      </header>

      {/* Tab nav */}
      <nav className="border-b border-border bg-bg-surface px-6">
        <div className="flex gap-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-mono border-b-2 transition-colors ${
                tab === t.id
                  ? "border-cargo-accent text-cargo-accent"
                  : "border-transparent text-muted hover:text-text-secondary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content — always mounted, hidden via CSS to prevent refetch on tab switch */}
      <main className="p-6">
        <div className={tab === "memory" ? "" : "hidden"}><MemoryBrowser /></div>
        <div className={tab === "similarity" ? "" : "hidden"}><VectorSimilarity /></div>
        <div className={tab === "schema" ? "" : "hidden"}><SchemaDriftPanel /></div>
        <div className={tab === "pending" ? "" : "hidden"}><PendingApprovals /></div>
      </main>
    </div>
  );
}

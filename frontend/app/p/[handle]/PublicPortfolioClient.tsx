"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface Asset {
  id: number;
  kind: "photo" | "file";
  url: string;
  sort_order: number;
}

interface PortfolioLink {
  id: number;
  label: string;
  url: string;
  kind: "social" | "messenger" | "website";
}

interface Portfolio {
  id: number;
  handle: string;
  headline: string;
  bio: string;
  hire_status: "open" | "closed" | "contract";
  assets: Asset[];
  links: PortfolioLink[];
}

const BADGE: Record<string, { label: string; color: string }> = {
  open:     { label: "Open to work",            color: "#22c55e" },
  contract: { label: "Available for contract",  color: "#f59e0b" },
  closed:   { label: "Not available",           color: "#ef4444" },
};

interface Props {
  handle: string;
}

export default function PublicPortfolioClient({ handle }: Props) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    if (!handle) return;
    fetch(`${API_BASE}/api/portfolio/public/${handle}`)
      .then((r) => {
        if (r.status === 404) { setNotFound(true); return null; }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => { if (data) setPortfolio(data as Portfolio); })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [handle]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
        <div style={{ width: 36, height: 36, border: "3px solid #e2e8f0", borderTopColor: "#2563EB", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (notFound || !portfolio) {
    return (
      <div style={{ maxWidth: 500, margin: "80px auto", textAlign: "center", fontFamily: "system-ui, sans-serif", color: "#1e293b", padding: "0 20px" }}>
        <h1 style={{ fontSize: "1.8rem", fontWeight: 800, marginBottom: 12 }}>Portfolio not found</h1>
        <p style={{ color: "#64748b", marginBottom: 24 }}>
          The portfolio <strong>@{handle}</strong> does not exist or has been removed.
        </p>
        <a href="/" style={{ background: "#2563EB", color: "#fff", padding: "10px 24px", borderRadius: 8, textDecoration: "none", fontWeight: 600 }}>
          Return to ResumeAI
        </a>
      </div>
    );
  }

  const badge = BADGE[portfolio.hire_status] ?? { label: portfolio.hire_status, color: "#94a3b8" };
  const photos = (portfolio.assets ?? []).filter((a) => a.kind === "photo");
  const files  = (portfolio.assets ?? []).filter((a) => a.kind === "file");

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#f8fafc", minHeight: "100vh", color: "#1e293b" }}>
      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.85)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", cursor: "zoom-out" }}
        >
          <img
            src={`${API_BASE}${lightbox}`}
            alt="Full size"
            style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: 8, objectFit: "contain" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Header */}
      <header style={{ background: "#fff", borderBottom: "1px solid #e2e8f0", padding: "0 24px" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", height: 56 }}>
          <a href="/" style={{ fontWeight: 800, color: "#2563EB", textDecoration: "none", fontSize: "1.1rem" }}>ResumeAI</a>
          <a href="/app" style={{ background: "#2563EB", color: "#fff", padding: "6px 16px", borderRadius: 8, fontWeight: 600, fontSize: "0.85rem", textDecoration: "none" }}>
            Create yours
          </a>
        </div>
      </header>

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px" }}>
        {/* Hero */}
        <div style={{ textAlign: "center", paddingBottom: 32, marginBottom: 32, borderBottom: "1px solid #e2e8f0" }}>
          <h1 style={{ fontSize: "clamp(1.6rem,4vw,2.2rem)", fontWeight: 800, color: "#0f172a", marginBottom: 8 }}>
            {portfolio.headline || portfolio.handle}
          </h1>
          <div style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: 12 }}>@{portfolio.handle}</div>
          <span style={{ display: "inline-block", padding: "4px 14px", borderRadius: 999, fontSize: "0.8rem", fontWeight: 600, color: "#fff", background: badge.color }}>
            {badge.label}
          </span>
          {portfolio.bio && (
            <p style={{ color: "#475569", maxWidth: 580, margin: "16px auto 0", lineHeight: 1.6 }}>
              {portfolio.bio}
            </p>
          )}
        </div>

        {/* Photo gallery */}
        {photos.length > 0 && (
          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>Photos</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
              {photos.map((photo) => (
                <div
                  key={photo.id}
                  onClick={() => setLightbox(photo.url)}
                  style={{ borderRadius: 10, overflow: "hidden", cursor: "zoom-in", aspectRatio: "4/3", background: "#e2e8f0" }}
                >
                  <img
                    src={`${API_BASE}${photo.url}`}
                    alt="Portfolio photo"
                    loading="lazy"
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", transition: "transform .2s" }}
                    onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.04)")}
                    onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                  />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* File attachments */}
        {files.length > 0 && (
          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>Files</h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {files.map((f) => (
                <a
                  key={f.id}
                  href={`${API_BASE}${f.url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", border: "1px solid #e2e8f0", borderRadius: 8, textDecoration: "none", color: "#1e293b", background: "#fff", fontWeight: 500, fontSize: "0.9rem" }}
                >
                  📄 {f.url.split("/").pop()}
                </a>
              ))}
            </div>
          </section>
        )}

        {/* Links grid */}
        {portfolio.links.length > 0 && (
          <section style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>Links</h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {portfolio.links.map((link) => {
                const icon = link.kind === "social" ? "🌐" : link.kind === "messenger" ? "💬" : "🔗";
                return (
                  <a
                    key={link.id}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", border: "1px solid #e2e8f0", borderRadius: 8, textDecoration: "none", color: "#1e293b", background: "#fff", fontWeight: 500, fontSize: "0.9rem" }}
                  >
                    {icon} {link.label}
                  </a>
                );
              })}
            </div>
          </section>
        )}
      </div>

      <footer style={{ textAlign: "center", color: "#94a3b8", fontSize: "0.8rem", padding: "24px 0", borderTop: "1px solid #e2e8f0" }}>
        © 2026 ResumeAI ·{" "}
        <a href="/privacy.html" style={{ color: "#94a3b8" }}>Privacy</a>
      </footer>
    </div>
  );
}

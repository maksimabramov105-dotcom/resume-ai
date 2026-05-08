"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function Spinner() {
  return (
    <>
      <div
        style={{
          width: 40,
          height: 40,
          border: "3px solid #E2E8F0",
          borderTopColor: "#2563EB",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <p style={{ color: "#64748B", margin: 0 }}>Signing you in…</p>
    </>
  );
}

function TelegramAuthInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "error">("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    const token = searchParams.get("t");
    if (!token) {
      setDetail("Missing link token.");
      setStatus("error");
      return;
    }

    let cancelled = false;

    async function exchange() {
      try {
        const res = await fetch(`${API_BASE}/api/auth/telegram-link`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (cancelled) return;

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setDetail(body.detail ?? `Error ${res.status}`);
          setStatus("error");
          return;
        }

        const data = await res.json();
        localStorage.setItem("auth_token", data.access_token ?? data.token);
        localStorage.setItem("user_id", String(data.user_id));
        router.replace("/app/dashboard");
      } catch {
        if (!cancelled) {
          setDetail("Network error — please try again.");
          setStatus("error");
        }
      }
    }

    exchange();
    return () => { cancelled = true; };
  }, [searchParams, router]);

  if (status === "loading") return <Spinner />;

  return (
    <>
      <p style={{ color: "#EF4444", fontWeight: 600, margin: 0 }}>Sign-in failed</p>
      <p style={{ color: "#64748B", margin: 0, maxWidth: 320 }}>{detail}</p>
      <a
        href="/app"
        style={{
          marginTop: 8,
          padding: "10px 24px",
          background: "#2563EB",
          color: "#fff",
          borderRadius: 8,
          textDecoration: "none",
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        Go to sign-in page
      </a>
    </>
  );
}

export default function TelegramAuthPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, -apple-system, sans-serif",
        background: "#F8FAFC",
        gap: "16px",
        padding: "24px",
        textAlign: "center",
      }}
    >
      <Suspense fallback={<Spinner />}>
        <TelegramAuthInner />
      </Suspense>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("auth_token") ?? "";
}

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

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
  sort_order: number;
}

interface Portfolio {
  id: number;
  handle: string;
  headline: string;
  bio: string;
  country: string;
  timezone: string;
  hire_status: "open" | "closed" | "contract";
  resume_blob_json?: string;
  assets: Asset[];
  links: PortfolioLink[];
}

const HIRE_STATUS_OPTIONS = [
  { value: "open", label: "Open to work" },
  { value: "contract", label: "Available for contract" },
  { value: "closed", label: "Not available" },
];

const LINK_KIND_OPTIONS = [
  { value: "social", label: "Social" },
  { value: "messenger", label: "Messenger" },
  { value: "website", label: "Website" },
];

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [handleError, setHandleError] = useState("");
  const [uploading, setUploading] = useState(false);

  // Form fields
  const [handle, setHandle] = useState("");
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [country, setCountry] = useState("");
  const [timezone, setTimezone] = useState("");
  const [hireStatus, setHireStatus] = useState<"open" | "closed" | "contract">("open");

  // New link form
  const [newLinkLabel, setNewLinkLabel] = useState("");
  const [newLinkUrl, setNewLinkUrl] = useState("");
  const [newLinkKind, setNewLinkKind] = useState<"social" | "messenger" | "website">("social");

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/portfolio`, { headers: authHeaders() })
      .then((r) => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Portfolio | null) => {
        if (data) {
          setPortfolio(data);
          setHandle(data.handle ?? "");
          setHeadline(data.headline ?? "");
          setBio(data.bio ?? "");
          setCountry(data.country ?? "");
          setTimezone(data.timezone ?? "");
          setHireStatus(data.hire_status ?? "open");
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setHandleError("");
    setSaveMsg("");
    setSaving(true);
    try {
      const body: Record<string, string> = {};
      if (handle) body.handle = handle.trim().toLowerCase();
      if (headline) body.headline = headline;
      if (bio) body.bio = bio;
      if (country) body.country = country;
      if (timezone) body.timezone = timezone;
      body.hire_status = hireStatus;

      const res = await fetch(`${API_BASE}/api/portfolio`, {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 409) setHandleError("Handle is already taken.");
        else if (res.status === 422) setHandleError(data.detail ?? "Validation error.");
        else setSaveMsg(`Error: ${data.detail ?? res.status}`);
        return;
      }
      setPortfolio(data as Portfolio);
      setSaveMsg("Saved successfully!");
      setTimeout(() => setSaveMsg(""), 3000);
    } finally {
      setSaving(false);
    }
  }

  async function handleFileUpload(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/portfolio/assets`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail ?? `Upload failed: ${res.status}`);
        return;
      }
      setPortfolio((prev) =>
        prev ? { ...prev, assets: [...prev.assets, data as Asset] } : prev
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteAsset(assetId: number) {
    if (!confirm("Delete this asset?")) return;
    const res = await fetch(`${API_BASE}/api/portfolio/assets/${assetId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    if (res.ok) {
      setPortfolio((prev) =>
        prev ? { ...prev, assets: prev.assets.filter((a) => a.id !== assetId) } : prev
      );
    }
  }

  async function handleAddLink() {
    if (!newLinkLabel || !newLinkUrl) {
      alert("Label and URL are required.");
      return;
    }
    const res = await fetch(`${API_BASE}/api/portfolio/links`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ label: newLinkLabel, url: newLinkUrl, kind: newLinkKind }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail ?? `Error: ${res.status}`);
      return;
    }
    setPortfolio((prev) =>
      prev ? { ...prev, links: [...prev.links, data as PortfolioLink] } : prev
    );
    setNewLinkLabel("");
    setNewLinkUrl("");
    setNewLinkKind("social");
  }

  async function handleDeleteLink(linkId: number) {
    if (!confirm("Delete this link?")) return;
    const res = await fetch(`${API_BASE}/api/portfolio/links/${linkId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    if (res.ok) {
      setPortfolio((prev) =>
        prev ? { ...prev, links: prev.links.filter((l) => l.id !== linkId) } : prev
      );
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="w-8 h-8 border-2 border-white/20 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        {portfolio?.handle && (
          <a
            href={`/p/${portfolio.handle}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-400 hover:text-blue-300 underline"
          >
            View public page →
          </a>
        )}
      </div>

      {/* Basic info */}
      <section className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Profile</h2>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Handle (public URL: /p/your-handle)</label>
          <input
            className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            value={handle}
            onChange={(e) => { setHandle(e.target.value); setHandleError(""); }}
            placeholder="e.g. jane-smith-42"
          />
          {handleError && <p className="text-red-400 text-xs mt-1">{handleError}</p>}
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Headline</label>
          <input
            className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="Senior Python Developer"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Bio</label>
          <textarea
            className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 min-h-[80px] resize-y"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="A short bio about yourself..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Country</label>
            <input
              className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="e.g. Germany"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Timezone</label>
            <input
              className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="e.g. Europe/Berlin"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Hire Status</label>
          <select
            className="w-full bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            value={hireStatus}
            onChange={(e) => setHireStatus(e.target.value as "open" | "closed" | "contract")}
          >
            {HIRE_STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-5 py-2 rounded-lg text-sm transition"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saveMsg && <p className="text-green-400 text-sm">{saveMsg}</p>}
      </section>

      {/* Photos */}
      <section className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Photos & Files</h2>
        <p className="text-xs text-gray-600">Max 10 assets, 5 MB each.</p>

        <div className="grid grid-cols-3 gap-3">
          {(portfolio?.assets ?? []).map((asset) => (
            <div key={asset.id} className="relative group rounded-lg overflow-hidden bg-[#1e1e1e] border border-white/10 aspect-square flex items-center justify-center">
              {asset.kind === "photo" ? (
                <img
                  src={`${API_BASE}${asset.url}`}
                  alt="Asset"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center text-xs text-gray-500 p-2">
                  <div className="text-2xl mb-1">📄</div>
                  <div className="truncate max-w-[80px]">{asset.url.split("/").pop()}</div>
                </div>
              )}
              <button
                onClick={() => handleDeleteAsset(asset.id)}
                className="absolute top-1 right-1 bg-red-600/80 hover:bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition"
              >
                ×
              </button>
            </div>
          ))}

          {(portfolio?.assets?.length ?? 0) < 10 && (
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="aspect-square rounded-lg border-2 border-dashed border-white/20 hover:border-blue-500/50 flex flex-col items-center justify-center text-gray-500 hover:text-gray-300 transition disabled:opacity-50"
            >
              {uploading ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-blue-500 rounded-full animate-spin" />
              ) : (
                <>
                  <span className="text-2xl">+</span>
                  <span className="text-xs mt-1">Upload</span>
                </>
              )}
            </button>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.doc,.docx"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFileUpload(f);
            e.target.value = "";
          }}
        />
      </section>

      {/* Links */}
      <section className="bg-[#141414] border border-white/[0.07] rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Links</h2>

        <div className="space-y-2">
          {(portfolio?.links ?? []).map((link) => (
            <div key={link.id} className="flex items-center gap-3 bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2">
              <span className="text-lg">{link.kind === "social" ? "🌐" : link.kind === "messenger" ? "💬" : "🔗"}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white font-medium truncate">{link.label}</div>
                <div className="text-xs text-gray-500 truncate">{link.url}</div>
              </div>
              <button
                onClick={() => handleDeleteLink(link.id)}
                className="text-red-400 hover:text-red-300 text-sm"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="border-t border-white/[0.07] pt-4 space-y-3">
          <p className="text-xs text-gray-500 font-medium">Add a link</p>
          <div className="grid grid-cols-2 gap-3">
            <input
              className="bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="Label (e.g. LinkedIn)"
              value={newLinkLabel}
              onChange={(e) => setNewLinkLabel(e.target.value)}
            />
            <select
              className="bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              value={newLinkKind}
              onChange={(e) => setNewLinkKind(e.target.value as "social" | "messenger" | "website")}
            >
              {LINK_KIND_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-3">
            <input
              className="flex-1 bg-[#1e1e1e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              placeholder="https://..."
              value={newLinkUrl}
              onChange={(e) => setNewLinkUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddLink()}
            />
            <button
              onClick={handleAddLink}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg text-sm transition"
            >
              Add
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

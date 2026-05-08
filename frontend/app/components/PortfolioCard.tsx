"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface Asset {
  id: number;
  kind: "photo" | "file";
  url: string;
}

interface PortfolioCardProps {
  handle: string;
  headline?: string;
  bio?: string;
  hire_status?: "open" | "closed" | "contract";
  assets?: Asset[];
}

const BADGE: Record<string, { label: string; color: string }> = {
  open:     { label: "Open to work",           color: "bg-green-500/20 text-green-400 border border-green-500/30" },
  contract: { label: "Available for contract", color: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30" },
  closed:   { label: "Not available",          color: "bg-red-500/20 text-red-400 border border-red-500/30" },
};

export default function PortfolioCard({ handle, headline, bio, hire_status = "open", assets = [] }: PortfolioCardProps) {
  const badge = BADGE[hire_status] ?? { label: hire_status, color: "bg-gray-500/20 text-gray-400 border border-gray-500/30" };
  const firstPhoto = assets.find((a) => a.kind === "photo");

  return (
    <a
      href={`/p/${handle}`}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-[#141414] border border-white/[0.07] rounded-2xl overflow-hidden hover:border-blue-500/30 transition group"
    >
      {firstPhoto && (
        <div className="aspect-video overflow-hidden bg-[#1e1e1e]">
          <img
            src={`${API_BASE}${firstPhoto.url}`}
            alt={headline ?? handle}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        </div>
      )}
      <div className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-white truncate">{headline || handle}</h3>
            <p className="text-xs text-gray-500">@{handle}</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${badge.color}`}>
            {badge.label}
          </span>
        </div>
        {bio && (
          <p className="text-xs text-gray-400 line-clamp-2">{bio}</p>
        )}
      </div>
    </a>
  );
}

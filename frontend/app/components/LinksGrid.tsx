"use client";

interface PortfolioLink {
  id: number;
  label: string;
  url: string;
  kind: "social" | "messenger" | "website";
}

interface LinksGridProps {
  links: PortfolioLink[];
}

const KIND_ICON: Record<string, string> = {
  social:    "🌐",
  messenger: "💬",
  website:   "🔗",
};

// Well-known domain → icon mapping
function iconForUrl(url: string, kind: string): string {
  const lower = url.toLowerCase();
  if (lower.includes("linkedin.com"))  return "💼";
  if (lower.includes("github.com"))    return "🐙";
  if (lower.includes("twitter.com") || lower.includes("x.com")) return "🐦";
  if (lower.includes("t.me") || lower.includes("telegram")) return "✈️";
  if (lower.includes("youtube.com"))  return "▶️";
  if (lower.includes("instagram.com")) return "📷";
  if (lower.includes("dribbble.com")) return "🏀";
  if (lower.includes("behance.net"))  return "🎨";
  return KIND_ICON[kind] ?? "🔗";
}

export default function LinksGrid({ links }: LinksGridProps) {
  if (!links.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
      {links.map((link) => (
        <a
          key={link.id}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 16px",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            textDecoration: "none",
            color: "#1e293b",
            background: "#fff",
            fontWeight: 500,
            fontSize: "0.9rem",
            transition: "background .15s, border-color .15s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "#f1f5f9";
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "#cbd5e1";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "#fff";
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "#e2e8f0";
          }}
        >
          <span aria-hidden="true">{iconForUrl(link.url, link.kind)}</span>
          {link.label}
        </a>
      ))}
    </div>
  );
}

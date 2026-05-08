"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface Photo {
  id: number;
  url: string;
  sort_order?: number;
}

interface PhotoGalleryProps {
  photos: Photo[];
}

export default function PhotoGallery({ photos }: PhotoGalleryProps) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  if (!photos.length) return null;

  function openAt(index: number) {
    setLightboxIndex(index);
    setLightboxUrl(photos[index].url);
  }

  function prev() {
    const idx = (lightboxIndex - 1 + photos.length) % photos.length;
    setLightboxIndex(idx);
    setLightboxUrl(photos[idx].url);
  }

  function next() {
    const idx = (lightboxIndex + 1) % photos.length;
    setLightboxIndex(idx);
    setLightboxUrl(photos[idx].url);
  }

  return (
    <>
      {/* Lightbox — pure CSS, no deps */}
      {lightboxUrl && (
        <div
          onClick={() => setLightboxUrl(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,.9)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Prev */}
          {photos.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); prev(); }}
              style={{ position: "absolute", left: 16, background: "rgba(255,255,255,.15)", border: "none", color: "#fff", borderRadius: "50%", width: 40, height: 40, cursor: "pointer", fontSize: "1.2rem" }}
            >
              ‹
            </button>
          )}

          <img
            src={`${API_BASE}${lightboxUrl}`}
            alt="Full size"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "88vw", maxHeight: "88vh", borderRadius: 8, objectFit: "contain", cursor: "default" }}
          />

          {/* Next */}
          {photos.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); next(); }}
              style={{ position: "absolute", right: 16, background: "rgba(255,255,255,.15)", border: "none", color: "#fff", borderRadius: "50%", width: 40, height: 40, cursor: "pointer", fontSize: "1.2rem" }}
            >
              ›
            </button>
          )}

          {/* Close */}
          <button
            onClick={() => setLightboxUrl(null)}
            style={{ position: "absolute", top: 16, right: 16, background: "rgba(255,255,255,.15)", border: "none", color: "#fff", borderRadius: "50%", width: 36, height: 36, cursor: "pointer", fontSize: "1rem" }}
          >
            ×
          </button>

          {/* Counter */}
          {photos.length > 1 && (
            <div style={{ position: "absolute", bottom: 16, color: "#ffffff99", fontSize: "0.85rem" }}>
              {lightboxIndex + 1} / {photos.length}
            </div>
          )}
        </div>
      )}

      {/* Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 10,
        }}
      >
        {photos.map((photo, i) => (
          <div
            key={photo.id}
            onClick={() => openAt(i)}
            style={{
              borderRadius: 10,
              overflow: "hidden",
              cursor: "zoom-in",
              aspectRatio: "4/3",
              background: "#e2e8f0",
            }}
          >
            <img
              src={`${API_BASE}${photo.url}`}
              alt={`Photo ${i + 1}`}
              loading="lazy"
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", transition: "transform .2s" }}
              onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.05)")}
              onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
            />
          </div>
        ))}
      </div>
    </>
  );
}

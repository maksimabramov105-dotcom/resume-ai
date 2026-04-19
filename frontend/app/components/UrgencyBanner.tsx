"use client";

import { useState, useEffect } from "react";

const TOTAL_SPOTS = 100;
const SPOTS_TAKEN = 34;

export default function UrgencyBanner() {
  const [spotsLeft, setSpotsLeft] = useState(TOTAL_SPOTS - SPOTS_TAKEN);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const dismissed = sessionStorage.getItem("urgency_dismissed");
    if (dismissed) setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <div className="bg-blue-700 text-white text-center py-2.5 px-4 relative">
      <p className="text-sm font-medium">
        🔥 <strong>First 100 users</strong> get 30 days Pro free —{" "}
        <span className="underline">{spotsLeft} spots left</span>
      </p>
      <button
        onClick={() => {
          setVisible(false);
          sessionStorage.setItem("urgency_dismissed", "1");
        }}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-lg leading-none"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

"use client";

// Lazy video player (D-AC2): the iframe is only mounted after the user taps the poster,
// so a lesson list or view never loads N third-party players up front. YouTube gets a real
// thumbnail poster; Vimeo (no keyless thumbnail) gets a neutral play panel.

import { useState } from "react";

import { videoEmbed } from "@/lib/app/academy";
import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

export function VideoEmbed({ url, title }: { url: string; title: string }) {
  const [playing, setPlaying] = useState(false);
  const v = videoEmbed(url);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: "16 / 9",
        background: "#000",
        borderRadius: 10,
        overflow: "hidden",
        border: `1px solid ${C.border}`,
      }}
    >
      {playing ? (
        <iframe
          src={`${v.embedUrl}${v.embedUrl.includes("?") ? "&" : "?"}autoplay=1`}
          title={title}
          loading="lazy"
          allow="accelerated-motion; autoplay; encrypted-media; picture-in-picture"
          allowFullScreen
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", border: "none" }}
        />
      ) : (
        <button
          type="button"
          onClick={() => setPlaying(true)}
          aria-label={`Play ${title}`}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            border: "none",
            cursor: "pointer",
            padding: 0,
            background: v.poster
              ? `center / cover no-repeat url(${v.poster})`
              : "linear-gradient(135deg, #10151d, #0b0d12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 18px",
              borderRadius: 24,
              background: "rgba(11,13,18,.72)",
              border: `1px solid ${C.green}`,
              color: C.green,
              font: `600 11px ${MONO}`,
              letterSpacing: 1,
            }}
          >
            ▶ PLAY
          </span>
        </button>
      )}
    </div>
  );
}

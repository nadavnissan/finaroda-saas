// Academy 2.0 (Stage 6) pure client logic: search + filtering (D-AC4, client-side over the
// user's visible list) and video-embed parsing. No React / UI deps -> unit-tested directly.

import type { AcademyLesson } from "@/lib/app/types";

export type LessonType = "all" | "text" | "video";
export type LessonState = "all" | "locked" | "unlocked" | "completed";

export interface LessonFilter {
  q: string;
  type: LessonType;
  state: LessonState;
}

export const EMPTY_LESSON_FILTER: LessonFilter = { q: "", type: "all", state: "all" };

// A lesson's visible state for the card badge and the state filter.
export function lessonState(l: AcademyLesson): "locked" | "completed" | "open" {
  if (!l.unlocked) return "locked";
  if (l.completed) return "completed";
  return "open";
}

// Client-side search over title/description/tags + type + lock/completion state, combined
// with AND. Instant, no server round-trip (Academy scale does not justify server search).
export function filterLessons(lessons: AcademyLesson[], f: LessonFilter): AcademyLesson[] {
  const q = f.q.trim().toLowerCase();
  return lessons.filter((l) => {
    if (f.type !== "all" && l.content_type !== f.type) return false;
    if (f.state !== "all") {
      const st = lessonState(l);
      // "unlocked" = accessible (includes completed); "completed" narrows to done.
      if (f.state === "locked" && st !== "locked") return false;
      if (f.state === "completed" && st !== "completed") return false;
      if (f.state === "unlocked" && st === "locked") return false;
    }
    if (q) {
      const hay = [l.title, l.description, ...(l.tags ?? [])].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// ── Video embed parsing (backend already normalizes to an embed URL) ──────────
export interface VideoEmbed {
  provider: "youtube" | "vimeo" | "unknown";
  embedUrl: string;
  poster: string | null; // a thumbnail for the lazy-load poster, when derivable
}

export function videoEmbed(url: string): VideoEmbed {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtube.com") && u.pathname.startsWith("/embed/")) {
      const id = u.pathname.split("/")[2] ?? "";
      return {
        provider: "youtube",
        embedUrl: url,
        poster: id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null,
      };
    }
    if (u.hostname.includes("vimeo.com")) {
      return { provider: "vimeo", embedUrl: url, poster: null };
    }
  } catch {
    /* fall through */
  }
  return { provider: "unknown", embedUrl: url, poster: null };
}

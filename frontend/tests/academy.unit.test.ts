// Academy 2.0 (Stage 6) unit tests: client-side search + filter combinations, lesson
// state, and video-embed parsing.
// Run: node --test --experimental-strip-types tests/academy.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  EMPTY_LESSON_FILTER,
  filterLessons,
  lessonState,
  videoEmbed,
} from "../src/lib/app/academy.ts";
import type { AcademyLesson } from "../src/lib/app/types.ts";

function mk(p: Partial<AcademyLesson>): AcademyLesson {
  return {
    slug: p.slug ?? "s", id: p.slug ?? "s", title: p.title ?? "Title",
    description: p.description ?? "", content_type: p.content_type ?? "text",
    duration_minutes: p.duration_minutes ?? 10, minutes: p.duration_minutes ?? 10,
    tags: p.tags ?? [], min_plan: p.min_plan ?? "free", min_rank: p.min_rank ?? 0,
    sort_index: p.sort_index ?? 0, unlocked: p.unlocked ?? true,
    completed: p.completed ?? false, awards_xp: p.awards_xp ?? true,
    lock_reason: p.lock_reason ?? null,
  };
}

const LESSONS: AcademyLesson[] = [
  mk({ slug: "a", title: "EMA7 timing", description: "the verified slope", tags: ["ema7", "edge"], content_type: "text", unlocked: true, completed: false }),
  mk({ slug: "b", title: "Risk geometry", description: "R sizing", tags: ["risk"], content_type: "video", unlocked: true, completed: true }),
  mk({ slug: "c", title: "Spike anatomy", description: "why most fade", tags: ["spike", "bonus"], content_type: "text", unlocked: false, completed: false, lock_reason: "Unlocks at Risk Manager" }),
];

// ── lessonState ──────────────────────────────────────────────────────────────
test("lessonState maps unlocked/completed correctly", () => {
  assert.equal(lessonState(LESSONS[0]), "open");
  assert.equal(lessonState(LESSONS[1]), "completed");
  assert.equal(lessonState(LESSONS[2]), "locked");
});

// ── filters ──────────────────────────────────────────────────────────────────
test("empty filter returns all lessons", () => {
  assert.equal(filterLessons(LESSONS, EMPTY_LESSON_FILTER).length, 3);
});

test("type filter narrows to video / text", () => {
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, type: "video" }).map((l) => l.slug), ["b"]);
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, type: "text" }).map((l) => l.slug), ["a", "c"]);
});

test("state filter: locked / unlocked / completed", () => {
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, state: "locked" }).map((l) => l.slug), ["c"]);
  // unlocked = accessible (includes completed)
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, state: "unlocked" }).map((l) => l.slug), ["a", "b"]);
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, state: "completed" }).map((l) => l.slug), ["b"]);
});

test("search matches title, description, and tags", () => {
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, q: "slope" }).map((l) => l.slug), ["a"]); // description
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, q: "spike" }).map((l) => l.slug), ["c"]);   // tag
  assert.deepEqual(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, q: "risk" }).map((l) => l.slug), ["b"]);    // title + tag
  assert.equal(filterLessons(LESSONS, { ...EMPTY_LESSON_FILTER, q: "nomatch" }).length, 0);
});

test("filters combine with AND (type + state + search)", () => {
  // text AND locked AND 'spike' -> only lesson c
  const out = filterLessons(LESSONS, { q: "spike", type: "text", state: "locked" });
  assert.deepEqual(out.map((l) => l.slug), ["c"]);
  // video AND locked -> none (b is unlocked)
  assert.equal(filterLessons(LESSONS, { q: "", type: "video", state: "locked" }).length, 0);
});

// ── video embed parsing ──────────────────────────────────────────────────────
test("videoEmbed derives a YouTube poster from an embed URL", () => {
  const v = videoEmbed("https://www.youtube.com/embed/dQw4w9WgXcQ");
  assert.equal(v.provider, "youtube");
  assert.equal(v.poster, "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg");
});

test("videoEmbed handles Vimeo (no poster) and unknown urls", () => {
  assert.equal(videoEmbed("https://player.vimeo.com/video/12345678").provider, "vimeo");
  assert.equal(videoEmbed("https://player.vimeo.com/video/12345678").poster, null);
  assert.equal(videoEmbed("not a url").provider, "unknown");
});

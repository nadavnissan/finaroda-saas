import { DISCLAIMER } from "@/lib/strings";

// legal — ToS / privacy / "analysis not advice" framing (SPEC §2.3; LEGAL.md).
// P0 placeholder only. Final copy pending lawyer review.
export default function LegalPage() {
  return (
    <main>
      <h1>Legal</h1>
      <p>Placeholder: Terms, Privacy &amp; disclaimer (pending lawyer review).</p>
      <small>{DISCLAIMER}</small>
    </main>
  );
}

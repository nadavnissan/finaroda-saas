import { APP_NAME, DISCLAIMER } from "@/lib/strings";

export default function Home() {
  return (
    <main>
      <h1>{APP_NAME}</h1>
      <p>Scan → score → decision board.</p>
      <small>{DISCLAIMER}</small>
    </main>
  );
}

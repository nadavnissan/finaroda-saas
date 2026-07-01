// checkout/success — Cardcom SuccessRedirectUrl target (SPEC §9).
export default function CheckoutSuccessPage() {
  return (
    <main>
      <h1>Payment received</h1>
      <p>Your subscription is active. Welcome to FINARODA.</p>
      <a href="/scan">Go to scan</a>
    </main>
  );
}

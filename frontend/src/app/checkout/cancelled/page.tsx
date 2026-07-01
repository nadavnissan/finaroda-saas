// checkout/cancelled — Cardcom FailedRedirectUrl target (SPEC §9).
export default function CheckoutCancelledPage() {
  return (
    <main>
      <h1>Checkout cancelled</h1>
      <p>No charge was made. You can try again anytime.</p>
      <a href="/paywall">Back to plans</a>
    </main>
  );
}

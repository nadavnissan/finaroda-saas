// checkout/success — Stripe Checkout success_url target (Stage 3R). Stripe appends
// ?session_id=... here. Activation is confirmed server-side by the webhook, never by this
// redirect, so we only welcome the user and send them to the app.
export default function CheckoutSuccessPage() {
  return (
    <main>
      <h1>Payment received</h1>
      <p>Thank you. Your subscription is being activated. Welcome to FINARODA.</p>
      <a href="/scan">Go to scan</a>
    </main>
  );
}

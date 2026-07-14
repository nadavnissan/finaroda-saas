// checkout — Stripe hosted Checkout (Stage 3R). Users are sent straight to Stripe's hosted
// page from /subscribe (api.initiateCheckout returns a redirect_url), so this route is only
// a fallback landing. The success and cancelled sub-routes are the Stripe return targets.
export default function CheckoutPage() {
  return (
    <main>
      <h1>Checkout</h1>
      <p>Redirecting you to secure checkout. If nothing happens, return to plans.</p>
      <a href="/subscribe">Back to plans</a>
    </main>
  );
}

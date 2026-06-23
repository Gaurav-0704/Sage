import { api } from "./api";

const CHECKOUT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

function loadScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = CHECKOUT_SRC;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

/**
 * Run the full Razorpay flow: create order → open checkout → verify → record.
 * Resolves to the recorded payment on success; throws on failure/cancel.
 */
export async function payOnline({ studentId, amount, feeHead }) {
  const cfg = (await api.get("/payments/razorpay/config")).data;
  if (!cfg.enabled) throw new Error("Online payment is not configured by the school.");

  const order = (await api.post("/payments/razorpay/order", {
    student_id: studentId, amount: Number(amount), fee_head: feeHead || null,
  })).data;

  const ok = await loadScript();
  if (!ok) throw new Error("Could not load the payment gateway. Check your connection.");

  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: "Sage",
      description: `Fees for ${order.student_name}`,
      handler: async (resp) => {
        try {
          const payment = (await api.post("/payments/razorpay/verify", {
            student_id: studentId, amount: Number(amount), fee_head: feeHead || null,
            razorpay_order_id: resp.razorpay_order_id,
            razorpay_payment_id: resp.razorpay_payment_id,
            razorpay_signature: resp.razorpay_signature,
          })).data;
          resolve(payment);
        } catch (e) {
          reject(new Error(e?.response?.data?.detail || "Payment verification failed"));
        }
      },
      modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
    });
    rzp.open();
  });
}

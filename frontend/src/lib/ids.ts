/**
 * Random Idempotency-Key for job submission (matches the server's
 * `^[A-Za-z0-9._:-]{8,100}$`). `crypto.randomUUID` needs a secure context, so
 * fall back to `getRandomValues`, which works on plain-HTTP development hosts.
 */
export function newIdempotencyKey(): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi.randomUUID === "function") {
    try {
      return cryptoApi.randomUUID();
    } catch {
      // Insecure context: use the fallback below.
    }
  }
  const bytes = new Uint8Array(16);
  cryptoApi.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

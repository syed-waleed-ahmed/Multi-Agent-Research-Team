/**
 * Copy text to the clipboard. Uses the async Clipboard API when available
 * (secure contexts) and falls back to a temporary selection otherwise.
 */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Permission denied or document not focused: try the fallback.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  textarea.select();
  let ok: boolean;
  try {
    // Legacy API, used only where the Clipboard API is unavailable.
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  textarea.remove();
  previousFocus?.focus();
  return ok;
}

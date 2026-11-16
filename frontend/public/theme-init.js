// Runs before first paint so the page never flashes the wrong theme.
// Kept as an external file because the Content-Security-Policy forbids inline scripts.
(function () {
  function read() {
    try {
      return window.localStorage.getItem("mart:theme");
    } catch {
      return null; // Storage blocked: fall back to the system preference.
    }
  }

  function systemPrefersDark() {
    try {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    } catch {
      return false;
    }
  }

  var stored = read();
  var dark = stored === "dark" || (stored !== "light" && systemPrefersDark());
  var root = document.documentElement;
  root.classList.toggle("dark", dark);
  root.style.colorScheme = dark ? "dark" : "light";
})();

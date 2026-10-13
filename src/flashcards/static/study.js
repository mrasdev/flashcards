// Keyboard control in study mode: Space reveals, K = known, N = not known.
// The listener is attached to the document and looks up the card on every key press,
// so it survives the HTMX swap of #study.
document.addEventListener("keydown", (event) => {
  // Synthetic events (e.g. from extensions) may come without a key or an element.
  if (typeof event.key !== "string" || !(event.target instanceof Element)) return;

  // Key combinations (e.g. Ctrl+K) and held keys do not count.
  if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) return;

  const target = event.target;
  if (target.closest("input, textarea, select") || target.isContentEditable) return;

  const details = document.querySelector("#study details[data-study-reveal]");
  if (!details) return;

  if (event.key === " ") {
    // With the card revealed or with Shift, Space belongs to the browser (scrolling).
    if (details.open || event.shiftKey) return;
    // On buttons and "Reveal" the browser handles Space itself,
    // on links it scrolls; do not interfere in either case.
    if (target.closest("button, a, summary")) return;
    event.preventDefault();
    details.open = true;
    return;
  }

  // Lower case so K/N also work with Caps Lock or Shift.
  const key = event.key.toLowerCase();
  if ((key === "k" || key === "n") && details.open) {
    const button = details.querySelector(`button[data-study-key="${key}"]`);
    if (button) {
      event.preventDefault();
      button.click();
    }
  }
});

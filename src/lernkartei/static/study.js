// Tastatursteuerung im Lernmodus: Leertaste deckt auf, J = gewusst, N = nicht gewusst.
// Der Listener hängt am Dokument und sucht die Karte bei jedem Tastendruck neu,
// damit er den HTMX-Austausch von #study übersteht.
document.addEventListener("keydown", (event) => {
  // Tastenkombinationen (z. B. Strg+J) und gehaltene Tasten zählen nicht.
  if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) return;

  const target = event.target;
  if (target.closest("input, textarea, select") || target.isContentEditable) return;

  const details = document.querySelector("#study details[data-study-reveal]");
  if (!details) return;

  if (event.key === " ") {
    // Auf Knöpfen, Links und "Aufdecken" löst der Browser die Leertaste selbst aus.
    if (target.closest("button, a, summary")) return;
    event.preventDefault();
    details.open = true;
    return;
  }

  // Kleinschreibung, damit J/N auch mit Feststelltaste oder Shift greifen.
  const key = event.key.toLowerCase();
  if ((key === "j" || key === "n") && details.open) {
    const button = details.querySelector(`button[data-study-key="${key}"]`);
    if (button) {
      event.preventDefault();
      button.click();
    }
  }
});

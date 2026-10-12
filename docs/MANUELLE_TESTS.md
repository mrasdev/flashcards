# Manuelle Browsertests

Verhalten, das die pytest-Suite nicht abdeckt, weil es erst im Browser entsteht. Nach Änderungen an den genannten Dateien von Hand durchgehen.

## Tastatursteuerung im Lernmodus

Betrifft `src/lernkartei/static/study.js` und `src/lernkartei/templates/partials/study_card.html`.

Vorbereitung: `uvicorn lernkartei.main:app --reload`, ein Deck mit mindestens drei fälligen Karten öffnen und auf „Lernen" klicken.

### Aufdecken

- [ ] Leertaste deckt die Karte auf, die Seite scrollt dabei nicht.
- [ ] Leertaste bei bereits aufgedeckter Karte klappt sie nicht wieder zu; die Seite scrollt wie gewohnt.
- [ ] Umschalt+Leertaste deckt nicht auf, die Seite scrollt nur zurück.
- [ ] Liegt der Fokus (per Tab) auf „Aufdecken", klappt die Leertaste die Karte genau einmal auf.

### Bewerten

- [ ] J und N tun bei zugeklappter Karte nichts.
- [ ] J bei aufgedeckter Karte wertet „Gewusst", die nächste Karte erscheint zugeklappt.
- [ ] N bei aufgedeckter Karte wertet „Nicht gewusst", die nächste Karte erscheint zugeklappt.
- [ ] Bei der nächsten Karte funktionieren Leertaste, J und N weiter, ohne die Seite neu zu laden.
- [ ] J und N funktionieren auch mit Feststelltaste und mit Umschalt (großes J/N).
- [ ] Das Fach der Karte stimmt danach auf der Deckseite (gewusst: ein Fach weiter, nicht gewusst: Fach 1).

### Schutz vor Fehleingaben

- [ ] Strg+J, Alt+J und AltGr+N lösen keine Bewertung aus.
- [ ] Eine gehalten gedrückte Taste (J oder N) bewertet nur eine Karte, nicht auch die folgende.
- [ ] Zweimal schnell J hintereinander bewertet nur die aktuelle Karte.
- [ ] Liegt der Fokus in einem Eingabefeld, greifen die Tasten nicht. Die Lernseite hat derzeit kein sichtbares Eingabefeld; zum Prüfen in den Entwicklerwerkzeugen vorübergehend ein `<input>` in `#study` einfügen und hineinklicken.

### Hinweis und Sitzungsende

- [ ] Unter der Karte steht der Tastenhinweis (Leertaste, J, N).
- [ ] Bei „Sitzung beendet." und „Fertig für heute!" fehlt der Hinweis, und die Tasten tun nichts.
- [ ] Die Browserkonsole zeigt während des Durchlaufs keine Fehler.

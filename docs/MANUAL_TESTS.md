# Manual browser tests

Behavior the pytest suite does not cover because it only arises in the browser. Go through it by hand after changing the files listed.

## Keyboard control in study mode

Affects `src/flashcards/static/study.js` and `src/flashcards/templates/partials/study_card.html`.

Preparation: run `uvicorn flashcards.main:app --reload`, open a deck with at least three due cards and click "Study".

### Reveal

- [ ] Space reveals the card, and the page does not scroll.
- [ ] Space on an already revealed card does not hide it again; the page scrolls as usual.
- [ ] Shift+Space does not reveal, the page only scrolls back.
- [ ] With the focus (via Tab) on "Reveal", Space reveals the card exactly once.

### Rate

- [ ] K and N do nothing while the card is hidden.
- [ ] K on a revealed card rates it "Known", and the next card appears hidden.
- [ ] N on a revealed card rates it "Not known", and the next card appears hidden.
- [ ] On the next card, Space, K and N keep working without reloading the page.
- [ ] K and N also work with Caps Lock and with Shift (upper-case K/N).
- [ ] The card's box is correct on the deck page afterwards (known: one box up, not known: box 1).

### Protection against accidental input

- [ ] Ctrl+K, Alt+K and AltGr+N do not trigger a rating.
- [ ] A held key (K or N) rates only one card, not the following one as well.
- [ ] Pressing K twice in quick succession rates only the current card.
- [ ] With the focus in an input field, the keys have no effect. The study page currently has no visible input field; to check, temporarily insert an `<input>` into `#study` in the developer tools and click into it.

### Hint and end of session

- [ ] The key hint (Space, K, N) is shown below the card.
- [ ] On "Session finished." and "Done for today!" the hint is missing and the keys do nothing.
- [ ] The browser console shows no errors during the run.

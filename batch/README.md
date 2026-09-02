# Batch order-form generator

Two tools that read the same CSV export of the "Sima" school-lunch order
Google Form (one row per family):

1. **Per-family order forms** — an order-form image (PNG) and real-text PDF
   per family, using the same visual design as the interactive form-filler
   (`../index.html`).
2. **Daily kitchen checklist** — a single PDF, one page per weekday, listing
   every girl with an order that day (alphabetical, with class shown and a
   checkbox to tick off) — for the kitchen/staff, not per-family.

## Files (code only - see note below)

- `day_utils.py` — shared CSV column names / "no meal that day" parsing used
  by both generators below, so they treat the data the same way.
- `order_form_generator.html` / `generate_orders.py` — per-family forms (1).
- `checklist_generator.html` / `generate_checklist.py` — daily checklist (2).

## Usage

1. Place a CSV export of the Google Form as `sima_meals.csv` in this folder
   (same column headers each time; not tracked by git — see below).
2. ```
   pip install playwright
   playwright install chromium   # one-time

   python3 generate_orders.py             # per-family: output/*.png + *.pdf, all rows
   python3 generate_orders.py 0 2 5       # per-family: just rows 1, 3, 6 (0-indexed)

   python3 generate_checklist.py          # daily checklist: output/checklist.pdf
   ```

## Note on this data

`sima_meals.csv` and everything under `output/` contain real students' names
and parents' phone numbers — both are gitignored on purpose and must never be
committed. Keep those files local, and delete old batches once they're no
longer needed operationally.

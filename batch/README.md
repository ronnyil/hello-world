# Batch order-form generator

Turns a CSV export of the "Sima" school-lunch order Google Form (one row per
family) into a per-family order-form image (PNG) and real-text PDF, using
the same visual design as the interactive form-filler (`../index.html`).

## Files (code only - see note below)

- `order_form_generator.html` — an offscreen page with the canvas/print-view
  rendering logic (adapted from the interactive site).
- `generate_orders.py` — reads a CSV export and drives
  `order_form_generator.html` through a headless browser to produce the
  output files.

## Usage

1. Place a CSV export of the Google Form as `sima_meals.csv` in this folder
   (same column headers each time; not tracked by git — see below).
2. ```
   pip install playwright
   playwright install chromium   # one-time
   python3 generate_orders.py             # generates output/*.png + *.pdf for all rows
   python3 generate_orders.py 0 2 5       # just rows 1, 3, 6 (0-indexed)
   ```

## Note on this data

`sima_meals.csv` and everything under `output/` contain real students' names
and parents' phone numbers — both are gitignored on purpose and must never be
committed. Keep those files local, and delete old batches once they're no
longer needed operationally.

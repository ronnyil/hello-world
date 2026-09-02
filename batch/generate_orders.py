"""
Generates a per-family order-form image (PNG) and real-text PDF from a CSV
export of the "Sima" school-lunch order Google Form, using the same visual
design as the interactive site (../index.html).

Usage:
    pip install playwright && playwright install chromium   # one-time
    python3 generate_orders.py                 # all rows
    python3 generate_orders.py 0 2 5            # just rows 1, 3, 6 (0-indexed)

Output goes to ./output/<row>_<student name>.png and .pdf

To use a different month's CSV export, replace sima_meals.csv (keep the
same column headers) and rerun.
"""
import csv
import re
import sys
import os
import base64
from playwright.sync_api import sync_playwright
from day_utils import DAY_NAMES, DAY_COLS, clean, day_text, student_name

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "sima_meals.csv")
GENERATOR_HTML = "file://" + os.path.join(HERE, "order_form_generator.html")
OUT_DIR = os.path.join(HERE, "output")
os.makedirs(OUT_DIR, exist_ok=True)

def row_to_data(row):
    days = []
    for name, col in zip(DAY_NAMES, DAY_COLS):
        days.append({"name": name, "text": day_text(row.get(col, ""))})
    return {
        "name": student_name(row),
        "phone": clean(row.get('שם ומספר טלפון לברורים', '')),
        "holder": clean(row.get('שם בעל הכרטיס המשלם ', '')),
        "days": days,
    }

def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "", name).strip() or "form"

def main(indices):
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if indices is None:
        indices = range(len(rows))

    with sync_playwright() as p:
        # This sandbox only has the full Chromium build installed (not the
        # default headless-shell variant); PLAYWRIGHT_CHROMIUM_PATH lets you
        # override this on a machine with a normal Playwright install.
        chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")
        launch_kwargs = {"executable_path": chromium_path} if os.path.exists(chromium_path) else {}
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 900, "height": 1300})
        page.goto(GENERATOR_HTML)
        page.wait_for_timeout(400)  # let the embedded logo image decode

        for i in indices:
            row = rows[i]
            data = row_to_data(row)
            base_name = f"{i+1:02d}_{safe_filename(data['name'])}"

            # PNG (canvas render) - handy for sending as a WhatsApp photo
            data_url = page.evaluate("(data) => renderOrderForm(data)", data)
            b64 = data_url.split(",", 1)[1]
            png_path = os.path.join(OUT_DIR, base_name + ".png")
            with open(png_path, "wb") as f:
                f.write(base64.b64decode(b64))

            # PDF (real selectable/searchable text, via the hidden print
            # view + Chromium's print-to-PDF)
            page.evaluate("(data) => renderOrderPrintView(data)", data)
            pdf_path = os.path.join(OUT_DIR, base_name + ".pdf")
            page.emulate_media(media="print")
            # Size the PDF page to the actual content instead of a fixed A4
            # sheet - otherwise the (short) order form leaves a large blank
            # area below it, which looks much sparser than the tightly
            # cropped PNG.
            content_height = page.evaluate("document.getElementById('printView').scrollHeight")
            page.pdf(
                path=pdf_path,
                width="827px",
                height=f"{content_height + 20}px",
                print_background=True,
            )
            page.emulate_media(media="screen")

            print(f"row {i+1}: {data['name']} -> {png_path} , {pdf_path}")

        browser.close()

if __name__ == "__main__":
    idx = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None
    main(idx)

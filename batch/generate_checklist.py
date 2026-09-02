"""
Generates a single multi-page PDF checklist for kitchen/staff use: one page
per weekday (Sun-Thu), listing the names (+ class) of every girl who has an
order that day, each with a checkbox to tick off - not per-family, unlike
generate_orders.py.

Usage:
    python3 generate_checklist.py               # -> output/checklist.pdf
"""
import csv
import os
from playwright.sync_api import sync_playwright
from day_utils import DAY_NAMES, DAY_COLS, is_no_order, student_name, student_class

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "sima_meals.csv")
GENERATOR_HTML = "file://" + os.path.join(HERE, "checklist_generator.html")
OUT_DIR = os.path.join(HERE, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def build_day_data(rows):
    days = []
    for day_name, col in zip(DAY_NAMES, DAY_COLS):
        students = []
        for row in rows:
            if not is_no_order(row.get(col, "")):
                students.append({"name": student_name(row), "klass": student_class(row)})
        students.sort(key=lambda s: s["name"])
        days.append({"dayName": day_name, "students": students})
    return days


def main():
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    day_data = build_day_data(rows)
    for d in day_data:
        print(f"{d['dayName']}: {len(d['students'])} תלמידות")

    with sync_playwright() as p:
        chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")
        launch_kwargs = {"executable_path": chromium_path} if os.path.exists(chromium_path) else {}
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.goto(GENERATOR_HTML)
        page.wait_for_timeout(200)

        page.evaluate("(data) => renderChecklist(data)", day_data)
        page.emulate_media(media="print")
        pdf_path = os.path.join(OUT_DIR, "checklist.pdf")
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()

    print("->", pdf_path)


if __name__ == "__main__":
    main()

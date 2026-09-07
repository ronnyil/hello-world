"""
Shared CSV-parsing helpers used by generate_orders.py (per-family forms)
and generate_checklist.py (daily kitchen checklist), so both agree on what
counts as "no meal that day" and read the same column names.
"""

DAY_NAMES = ["יום א׳", "יום ב׳", "יום ג׳", "יום ד׳", "יום ה׳"]
DAY_COLS = [
    'הזמנה ליום א ( ביום בו אין הזמנה כתבו X)',
    'הזמנה ליום ב',
    'הזמנה ליום ג',
    'הזמנה ליום ד',
    'הזמנה ליום ה',
]

# Anything a family has typed/tapped that means "no meal that day" - families
# haven't been consistent about this, so the list grows as new phrasings
# show up in real responses.
NO_ORDER_VALUES = {"x", "×", "אין", "כלום", "אין הזמנה", "❌", "בלי"}


def clean(s):
    return (s or "").strip()


def is_no_order(raw):
    return clean(raw).lower() in NO_ORDER_VALUES


def day_text(raw):
    """Display text for a day cell: the literal order, or the standard
    'X (no meal)' label if this is a no-order marker."""
    v = clean(raw)
    if is_no_order(v):
        return "X (אין הסעדה)"
    return v


def student_name(row):
    return clean(row.get('שם מלא של התלמידה', ''))


def student_class(row):
    return clean(row.get('כתה', ''))


def dedupe_latest(rows):
    """Collapse re-submissions: keep only the last row per student.

    Families sometimes fill the form a second time to change their order.
    The sheet keeps both rows, so counting them all would double-book the
    student on any day that appears in both. Rows arrive in submission
    order, so the later row wins.

    Returns (kept_rows, superseded) where superseded lists
    (student, dropped_row, kept_row) for reporting.
    """
    key_to_index = {}
    order = []
    superseded = []
    for row in rows:
        key = " ".join(student_name(row).split())
        if key in key_to_index:
            i = key_to_index[key]
            superseded.append((key, order[i], row))
            order[i] = row
        else:
            key_to_index[key] = len(order)
            order.append(row)
    return order, superseded

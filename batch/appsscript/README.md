# Apps Script renderer / mailer

Delivers order forms and the kitchen checklist by email, on a schedule,
without a human present.

## Why this exists

The assistant can read the responses sheet and resolve its messiness, but
it cannot deliver binary files. Every email/Drive tool available to it
takes attachment content as base64 text passed inline in a tool call, so
a 320KB PDF becomes ~430,000 characters that have to pass through the
model's own output — past the per-message limit.

Apps Script has the opposite problem: it can email a PDF trivially, but
it has no judgment about messy human input.

So the work is split along that line:

| | Does | Does not |
|---|---|---|
| Claude | reads the sheet, resolves discrepancies, decides | render or deliver binaries |
| Apps Script | renders HTML to PDF, emails it, on a timer | interpret anything |

Claude writes a fully resolved instruction file into the `commands`
folder. This script renders exactly what it is given. It never parses the
responses sheet, so there is nothing in it that can silently misread a
response.

## Why the data needs judgment at all

Measured across 44 real responses:

- **7 distinct spellings** of "no meal that day": `X` `x` `×` `❌` `אין`
  `כלום` `בלי`
- **`כן`** used as a day value (7 instances) — an order with no dish named
- **`בלי`** appearing inside a real dish (`שניצל ופסטה בלי תירס`), one
  matching rule away from silently dropping that student from Monday
- **`פרווה`** stated inside free text — a dietary requirement invisible to
  any counting logic
- **27 of 44** phone fields contain a parent's name alongside the number
- **4 spellings** of the school name
- **re-submissions**: families re-filing to change an order, where the
  later row must supersede the earlier one or the student is double-booked

None of these are resolvable by a fixed rule. All of them are resolved
before the instruction file is written.

## Setup

1. Create a project at script.google.com, paste in `Code.gs`.
2. Set `LOGO_FILE_ID` in `CONFIG` if you want the logo on the forms
   (upload a PNG/JPEG to Drive and use its file id). Leave `''` to skip.
   The folder ids are already filled in.
3. Run `setup` once and grant permissions. This installs a trigger that
   polls the commands folder every 5 minutes.
4. Run `selfTest`. You should get one email with two PDFs attached.

## Instruction file format

Written by Claude into the `commands` folder as JSON. Every value is
already resolved — the script does no interpretation.

```json
{
  "to": ["someone@example.com"],
  "subject": "עדכון המטבחון של סימה",
  "note": "free text shown in the email body",
  "forms": [
    {
      "student": "יעלה שפץ",
      "klass": "ז",
      "phone": "0506238073",
      "holder": "תמי זלצברג שפץ",
      "days": ["X (אין הסעדה)", "X (אין הסעדה)", "X (אין הסעדה)",
               "מוקפץ+ נודלס+ אפונה", "קציצות בשר + פסטה + תירס"],
      "dietary": ""
    }
  ],
  "checklist": [
    {
      "day": "יום א׳",
      "students": [{"name": "ליבי אדלמן", "klass": "ט", "note": "פרווה"}]
    }
  ]
}
```

`days` is always five entries in order א׳–ה׳. `dietary` and `note` are
free text and may be empty.

## Failure behaviour

A malformed or unrenderable instruction file is **not** silently skipped.
It is renamed `FAILED_<name>`, moved to `done`, and an error email is
sent. Silence means nothing arrived, not that something was quietly
dropped.

## Known limits

- **PDF only.** Apps Script converts HTML to PDF natively but has no
  HTML-to-PNG path. PNG would require rebuilding each form as a Google
  Slides page and exporting a thumbnail, which loses the CSS layout.
- **Not pixel-identical to the site.** Google's HTML-to-PDF converter
  supports a narrower slice of CSS than headless Chromium, so the layout
  is close to, not the same as, `batch/order_form_generator.html`.
- **Untested.** `script.google.com` is unreachable from the environment
  this was written in, so this code has never been executed. Expect to
  iterate on the first run.

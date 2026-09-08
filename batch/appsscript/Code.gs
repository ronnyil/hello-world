/**
 * המטבחון של סימה - renderer / mailer
 *
 * This script deliberately contains NO logic for interpreting the form
 * responses. Claude reads the responses sheet, resolves every discrepancy
 * (re-submissions, dietary notes, the seven different spellings of "no
 * meal", free text where a dish name was expected), and drops a fully
 * resolved instruction file into the commands folder.
 *
 * This script only renders that data and mails it. If it ever finds
 * itself guessing, that is a bug in the instruction file, not here.
 *
 * SETUP
 *   1. Paste this into a new Apps Script project (script.google.com).
 *   2. Fill in the three IDs in CONFIG below.
 *   3. Run `setup` once and grant the permissions it asks for.
 *      That installs a time-based trigger.
 *   4. Run `selfTest` to send yourself one sample form + checklist.
 */

var CONFIG = {
  // Drive folder Claude drops instruction files into.
  COMMANDS_FOLDER_ID: '1xEm9D22trdZwRqXLKjhQ-WTm7dOUrHnf',

  // Processed instruction files are moved here.
  DONE_FOLDER_ID: '1PhzaNvZVk2MLbxPaoI7yb8o2MVeSoiMG',

  // Optional. A PNG/JPEG logo in Drive, shown at the top of each form.
  // Leave '' to render without a logo.
  LOGO_FILE_ID: '',

  // How often to look for new instruction files.
  POLL_MINUTES: 5,

  // Fallback recipient if an instruction file omits "to".
  DEFAULT_TO: Session.getEffectiveUser().getEmail()
};

var DAY_NAMES = ['יום א׳', 'יום ב׳', 'יום ג׳', 'יום ד׳', 'יום ה׳'];


/* ------------------------------------------------------------------ */
/* setup                                                               */
/* ------------------------------------------------------------------ */

function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'processCommands') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('processCommands')
    .timeBased()
    .everyMinutes(CONFIG.POLL_MINUTES)
    .create();
  Logger.log('Trigger installed: processCommands every %s min',
             CONFIG.POLL_MINUTES);
}


/* ------------------------------------------------------------------ */
/* main loop                                                           */
/* ------------------------------------------------------------------ */

function processCommands() {
  var commands = DriveApp.getFolderById(CONFIG.COMMANDS_FOLDER_ID).getFiles();
  var done = DriveApp.getFolderById(CONFIG.DONE_FOLDER_ID);
  var handled = 0;

  while (commands.hasNext()) {
    var file = commands.next();
    try {
      var instruction = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
      handleInstruction(instruction);
      file.moveTo(done);
      handled++;
    } catch (err) {
      // Leave the file in place so the failure is visible rather than
      // silently swallowed, and report it.
      Logger.log('FAILED on %s: %s', file.getName(), err);
      notifyFailure(file.getName(), err);
      file.setName('FAILED_' + file.getName());
      file.moveTo(done);
    }
  }
  return handled;
}


function handleInstruction(instruction) {
  var attachments = [];

  (instruction.forms || []).forEach(function (form) {
    attachments.push(
      htmlToPdf(renderForm(form), safeName(form.student) + '.pdf')
    );
  });

  if (instruction.checklist && instruction.checklist.length) {
    attachments.push(
      htmlToPdf(renderChecklist(instruction.checklist), 'רשימת מטבח.pdf')
    );
  }

  if (!attachments.length) throw new Error('instruction produced no files');

  MailApp.sendEmail({
    to: (instruction.to && instruction.to.join(',')) || CONFIG.DEFAULT_TO,
    subject: instruction.subject || 'עדכון המטבחון של סימה',
    htmlBody: buildBody(instruction),
    attachments: attachments
  });
}


function notifyFailure(name, err) {
  MailApp.sendEmail({
    to: CONFIG.DEFAULT_TO,
    subject: 'המטבחון - שגיאה בעיבוד',
    body: 'Instruction file: ' + name + '\n\n' + err
  });
}


/* ------------------------------------------------------------------ */
/* rendering                                                           */
/* ------------------------------------------------------------------ */

function htmlToPdf(html, filename) {
  return Utilities.newBlob(html, 'text/html', filename)
                  .getAs('application/pdf')
                  .setName(filename);
}


function logoTag() {
  if (!CONFIG.LOGO_FILE_ID) return '';
  var cached = CacheService.getScriptCache().get('logo');
  if (!cached) {
    var blob = DriveApp.getFileById(CONFIG.LOGO_FILE_ID).getBlob();
    cached = 'data:' + blob.getContentType() + ';base64,' +
             Utilities.base64Encode(blob.getBytes());
    // Cache is capped at 100KB per key; skip caching if the logo is large.
    if (cached.length < 90000) {
      CacheService.getScriptCache().put('logo', cached, 21600);
    }
  }
  return '<img src="' + cached + '" style="width:90px;margin:0 auto 6px;display:block">';
}


function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


function baseCss() {
  return '<style>' +
    'body{font-family:Arial,Helvetica,sans-serif;direction:rtl;margin:28px;color:#222}' +
    '.hdr{text-align:center;border-bottom:1px solid #ddd;padding-bottom:10px;margin-bottom:14px}' +
    '.bsd{font-size:20px;font-weight:bold;margin:2px 0}' +
    '.sub{font-size:11px;color:#666}' +
    '.kosher{color:#b3312c;font-weight:bold;text-align:center;font-size:13px;margin:8px 0 2px}' +
    'h1{font-size:22px;text-align:center;margin:4px 0}' +
    'h2{font-size:17px;text-align:center;color:#7a6a53;margin:0 0 14px;font-weight:normal}' +
    '.row{margin:7px 0;font-size:14px}' +
    '.lbl{font-weight:bold}' +
    '.val{color:#b3312c}' +
    '.rule{border:0;border-top:1px solid #eee;margin:16px 0}' +
    '.menu{font-size:14px;margin:6px 0}' +
    '.note{color:#b3312c;font-weight:bold}' +
    'table{width:100%;border-collapse:collapse;font-size:12px}' +
    'td{padding:4px 6px;border-bottom:1px solid #eee}' +
    '.num{color:#999;width:26px}' +
    '.box{width:16px}' +
    '.day{font-size:24px;color:#b3312c;text-align:center;font-weight:bold;margin:0}' +
    '.cnt{text-align:center;color:#666;font-size:12px;margin:2px 0 12px}' +
    '</style>';
}


function renderForm(form) {
  var h = ['<!DOCTYPE html><html><head><meta charset="UTF-8">', baseCss(),
           '</head><body>'];
  h.push('<div class="hdr">', logoTag(),
         '<div class="bsd">בס"ד</div>',
         '<div class="sub">טלפון להזמנות: 08-9265368 | חירום: 050-5368405</div></div>');
  h.push('<div class="kosher">כשר בהשגחת הרב אלחרר</div>');
  h.push('<h1>טופס פרטים להרשמה</h1><h2>אולפנת שעלבים</h2>');

  h.push('<div class="row"><span class="lbl">שם התלמיד/ה:</span> ',
         '<span class="val">', esc(form.student), '</span></div>');
  h.push('<div class="row"><span class="lbl">טלפון נייד לבירורים:</span> ',
         '<span class="val">', esc(form.phone), '</span></div>');
  h.push('<div class="row"><span class="lbl">שם בעל הכרטיס:</span> ',
         '<span class="val">', esc(form.holder), '</span></div>');
  if (form.klass) {
    h.push('<div class="row"><span class="lbl">כתה:</span> ',
           '<span class="val">', esc(form.klass), '</span></div>');
  }

  h.push('<div class="row"><span class="lbl">מספר כרטיס אשראי:</span> ',
         '____  -  ____  -  ____  -  ____</div>');
  h.push('<div class="row" style="font-size:11px;color:#777">',
         '(לא ניתן לשלם באמריקן אקספרס)</div>');
  h.push('<div class="row"><span class="lbl">תוקף כרטיס אשראי:</span> ',
         '_______________</div>');
  h.push('<div class="row"><span class="lbl">שלוש ספרות אחרונות בגב הכרטיס:</span> ',
         '__________</div>');

  h.push('<hr class="rule"><div class="row lbl">פירוט תפריט:</div>');
  (form.days || []).forEach(function (text, i) {
    h.push('<div class="menu"><b>', DAY_NAMES[i] || '', '</b> - ', esc(text), '</div>');
  });

  if (form.dietary) {
    h.push('<div class="menu note">שים לב: ', esc(form.dietary), '</div>');
  }

  h.push('</body></html>');
  return h.join('');
}


function renderChecklist(days) {
  var h = ['<!DOCTYPE html><html><head><meta charset="UTF-8">', baseCss(),
           '</head><body>'];
  days.forEach(function (day, idx) {
    if (idx > 0) h.push('<div style="page-break-before:always"></div>');
    h.push('<div class="hdr">', logoTag(),
           '<div class="bsd">בס"ד</div>',
           '<div class="sub">אולפנת שעלבים</div></div>');
    h.push('<div class="day">', esc(day.day), '</div>');
    h.push('<div class="cnt">סה"כ ', (day.students || []).length,
           ' תלמידות מזמינות</div>');
    h.push('<table>');
    (day.students || []).forEach(function (s, i) {
      h.push('<tr><td class="num">', i + 1, '</td>',
             '<td class="box">&#9744;</td>',
             '<td><b>', esc(s.name), '</b></td>',
             '<td>', esc(s.klass), '</td>',
             '<td class="note">', esc(s.note || ''), '</td></tr>');
    });
    h.push('</table>');
  });
  h.push('</body></html>');
  return h.join('');
}


function buildBody(instruction) {
  var b = ['<div dir="rtl" style="font-family:Arial,sans-serif">'];
  b.push('<h2 style="color:#b3312c">עדכון המטבחון של סימה</h2>');
  if (instruction.note) b.push('<p>', instruction.note, '</p>');
  if ((instruction.forms || []).length) {
    b.push('<p><b>טפסים מצורפים:</b></p><ul>');
    instruction.forms.forEach(function (f) {
      b.push('<li>', esc(f.student), f.klass ? ' (כתה ' + esc(f.klass) + ')' : '', '</li>');
    });
    b.push('</ul>');
  }
  if ((instruction.checklist || []).length) {
    b.push('<p><b>רשימת מטבח:</b> ');
    b.push(instruction.checklist.map(function (d) {
      return esc(d.day) + ' - ' + (d.students || []).length;
    }).join(' · '));
    b.push('</p>');
  }
  b.push('</div>');
  return b.join('');
}


function safeName(s) {
  return String(s || 'form').replace(/[\\\/:*?"<>|]/g, '_').trim();
}


/* ------------------------------------------------------------------ */
/* self test                                                           */
/* ------------------------------------------------------------------ */

function selfTest() {
  handleInstruction({
    subject: 'בדיקה - המטבחון של סימה',
    note: 'הודעת בדיקה. אם הגיעה עם שני קבצים מצורפים - ההגדרה הושלמה.',
    forms: [{
      student: 'בדיקה בדיקה', klass: 'ז', phone: '0500000000',
      holder: 'הורה בדיקה',
      days: ['X (אין הסעדה)', 'שניצל ופסטה', 'קבב ואורז',
             'מוקפץ נודלס', 'קציצות עוף'],
      dietary: ''
    }],
    checklist: [{
      day: 'יום א׳',
      students: [{ name: 'בדיקה בדיקה', klass: 'ז', note: '' },
                 { name: 'בדיקה שנייה', klass: 'ח', note: 'פרווה' }]
    }]
  });
  Logger.log('selfTest sent to %s', CONFIG.DEFAULT_TO);
}

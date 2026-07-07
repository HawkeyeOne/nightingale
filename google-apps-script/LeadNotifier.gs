/**
 * Nightingale RN Academy lead notifications.
 *
 * This uses a one-minute clock trigger instead of onFormSubmit so it also works
 * when Tally or another integration writes rows into Google Sheets.
 */

const OWNER_EMAIL = 'nightingale.rn.academy@gmail.com';
const STATUS_HEADER = 'Notification Sent';

/**
 * Run this function once from Apps Script to initialize the status column,
 * preserve existing leads without emailing them, and install the trigger.
 */
function setupLeadNotifier() {
  const sheet = getLeadSheet_();
  const statusColumn = getOrCreateStatusColumn_(sheet);
  const lastRow = sheet.getLastRow();

  // Only leads added after setup should generate a notification.
  if (lastRow > 1) {
    const statusRange = sheet.getRange(2, statusColumn, lastRow - 1, 1);
    const statuses = statusRange.getDisplayValues();
    const initializedAt = `Existing before notifier — ${new Date().toISOString()}`;

    statusRange.setValues(
      statuses.map(([status]) => [status || initializedAt])
    );
  }

  // Prevent duplicate clock triggers if setup is run more than once.
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'sendNewLeadNotifications')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));

  ScriptApp.newTrigger('sendNewLeadNotifications')
    .timeBased()
    .everyMinutes(1)
    .create();
}

/**
 * Checks for unnotified rows, sends one email per lead, and stamps the row.
 * The script lock prevents overlapping trigger runs from sending duplicates.
 */
function sendNewLeadNotifications() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) return;

  try {
    const sheet = getLeadSheet_();
    const statusColumn = getOrCreateStatusColumn_(sheet);
    const lastRow = sheet.getLastRow();
    const lastColumn = sheet.getLastColumn();

    if (lastRow < 2) return;

    const headers = sheet.getRange(1, 1, 1, lastColumn).getDisplayValues()[0];
    const rows = sheet.getRange(2, 1, lastRow - 1, lastColumn).getDisplayValues();

    rows.forEach((row, index) => {
      const rowNumber = index + 2;
      const status = row[statusColumn - 1];
      const hasLeadData = row.some((value, columnIndex) =>
        columnIndex !== statusColumn - 1 && String(value).trim() !== ''
      );

      if (status || !hasLeadData) return;

      const lead = headers.reduce((result, header, columnIndex) => {
        if (columnIndex !== statusColumn - 1 && header) {
          result[header] = row[columnIndex];
        }
        return result;
      }, {});

      sendLeadEmail_(lead, sheet.getName(), rowNumber);
      sheet.getRange(rowNumber, statusColumn).setValue(new Date());
    });
  } finally {
    lock.releaseLock();
  }
}

function sendLeadEmail_(lead, sheetName, rowNumber) {
  const name = findField_(lead, ['full name', 'name']) || 'New lead';
  const course = findField_(lead, ['course', 'class', 'program']) || 'Course inquiry';
  const leadEmail = findField_(lead, ['email address', 'email']);
  const spreadsheetUrl = SpreadsheetApp.getActiveSpreadsheet().getUrl();

  const rows = Object.entries(lead)
    .filter(([, value]) => String(value).trim() !== '')
    .map(([label, value]) =>
      `<tr><th style="padding:8px 14px 8px 0;text-align:left;vertical-align:top;color:#52627a;">${escapeHtml_(label)}</th>` +
      `<td style="padding:8px 0;color:#172238;">${escapeHtml_(value)}</td></tr>`
    )
    .join('');

  const htmlBody = `
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#172238;">
      <div style="background:#061a3a;padding:22px 26px;border-radius:14px 14px 0 0;">
        <h1 style="margin:0;color:#fff;font-size:22px;">New website lead</h1>
        <p style="margin:6px 0 0;color:#e7b551;">${escapeHtml_(course)}</p>
      </div>
      <div style="padding:24px 26px;border:1px solid #dfe5ef;border-top:0;border-radius:0 0 14px 14px;">
        <table style="border-collapse:collapse;width:100%;">${rows}</table>
        <p style="margin:22px 0 0;font-size:13px;color:#6a7689;">
          Source: ${escapeHtml_(sheetName)}, row ${rowNumber} ·
          <a href="${spreadsheetUrl}" style="color:#0b5bd3;">Open spreadsheet</a>
        </p>
      </div>
    </div>`;

  const body = [
    'New website lead',
    '',
    ...Object.entries(lead)
      .filter(([, value]) => String(value).trim() !== '')
      .map(([label, value]) => `${label}: ${value}`),
    '',
    `Source: ${sheetName}, row ${rowNumber}`,
    spreadsheetUrl
  ].join('\n');

  const options = {
    to: OWNER_EMAIL,
    subject: `New lead: ${name} — ${course}`,
    body,
    htmlBody,
    name: 'Nightingale RN Academy Website'
  };

  if (leadEmail && leadEmail.includes('@')) options.replyTo = leadEmail;
  MailApp.sendEmail(options);
}

function getLeadSheet_() {
  const sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  if (sheets.length !== 1) {
    throw new Error('Expected exactly one sheet tab. Update getLeadSheet_ if tabs are added.');
  }
  return sheets[0];
}

function getOrCreateStatusColumn_(sheet) {
  const lastColumn = Math.max(sheet.getLastColumn(), 1);
  const headers = sheet.getRange(1, 1, 1, lastColumn).getDisplayValues()[0];
  const existingIndex = headers.findIndex(header => header.trim() === STATUS_HEADER);

  if (existingIndex >= 0) return existingIndex + 1;

  const statusColumn = lastColumn + 1;
  sheet.getRange(1, statusColumn).setValue(STATUS_HEADER).setFontWeight('bold');
  return statusColumn;
}

function findField_(lead, candidates) {
  const entries = Object.entries(lead);
  const match = entries.find(([header]) =>
    candidates.includes(header.trim().toLowerCase())
  );
  return match ? match[1] : '';
}

function escapeHtml_(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

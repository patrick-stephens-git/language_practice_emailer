// Google Apps Script web app: adds +1 to "Lookup Count" for a word when the emailed link is tapped.
// Bound to the sheet (Extensions > Apps Script). Set the LINK_SECRET script property to match .env.
// Deploy as a Web app: Execute as "Me", access "Anyone".

const SHEET_GID = 0; // numeric tab id (the number after gid= in the sheet URL); must match SHEET_GID in .env

function doGet(e) {
  const params = (e && e.parameter) || {};
  const secret = PropertiesService.getScriptProperties().getProperty('LINK_SECRET');

  if (!secret || params.key !== secret) return page_('Invalid link.');
  if (!params.word) return page_('Missing word.');

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sheet = SpreadsheetApp.getActive().getSheets().find(s => s.getSheetId() === SHEET_GID);
    if (!sheet) return page_('Sheet tab not found.');

    const values = sheet.getDataRange().getValues();
    const headers = values[0];
    const wordCol = headers.indexOf('Word');
    const countCol = headers.indexOf('Lookup Count');
    if (wordCol < 0 || countCol < 0) return page_('Missing "Word" or "Lookup Count" column.');

    for (let r = 1; r < values.length; r++) {
      if (String(values[r][wordCol]) === params.word) { // first exact match, same as the Python side
        const cell = sheet.getRange(r + 1, countCol + 1);
        cell.setValue((Number(cell.getValue()) || 0) + 1);
        return page_('Counted: ' + params.word);
      }
    }
    return page_('Word not found.');
  } finally {
    lock.releaseLock();
  }
}

function page_(message) {
  const safe = String(message).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return HtmlService.createHtmlOutput('<p style="font-family:sans-serif;font-size:1.2em">' + safe + '</p>');
}

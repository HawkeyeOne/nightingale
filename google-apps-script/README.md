# Google Sheets lead email setup

1. Open the lead spreadsheet.
2. Select **Extensions → Apps Script**.
3. Replace the editor contents with `LeadNotifier.gs`.
4. Save the project.
5. Select `setupLeadNotifier` from the function menu and click **Run** once.
6. Approve the requested Google Sheets and email permissions.

The setup function creates a one-minute trigger and a `Notification Sent`
column. Existing rows are marked during setup without sending email. New rows
added afterward are emailed to `nightingale.rn.academy@gmail.com` and stamped
after delivery so they are not sent twice.

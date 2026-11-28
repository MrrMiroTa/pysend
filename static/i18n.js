/* Language switch (English default / Khmer). Static page text is translated by matching the text in the HTML;
   text made by app.js goes through I18N.t("English text with {vars}", {vars}). The choice is kept in this browser. */
(function () {
  "use strict";
  var KEY = "lang", lang = "en";
  try { lang = localStorage.getItem(KEY) === "km" ? "km" : "en"; } catch (e) { /* private mode: English */ }
  var X = ""; // an empty translation hides a duplicate English/Khmer caption
  // key -> [English, Khmer]
  var D = {
    // ---- shell / nav ----
    "GPS Expiry Notifier": ["GPS Expiry Notifier", "ប្រព័ន្ធជូនដំណឹង GPS ផុតកំណត់"],
    "Notifier": ["Notifier", "ជូនដំណឹង"],
    "ផ្ទាំងគ្រប់គ្រង": ["Dashboard", "ផ្ទាំងគ្រប់គ្រង"], "Dashboard": [X, X],
    "របាយការណ៍": ["Report", "របាយការណ៍"], "Report": [X, X],
    "អ្នកប្រើប្រាស់": ["Users", "អ្នកប្រើប្រាស់"], "Users": [X, X],
    "One message per client, with a table of all their units.": ["One message per client, with a table of all their units.", "សារមួយក្នុងមួយអតិថិជន ជាមួយតារាងឧបករណ៍ទាំងអស់របស់គាត់។"],
    "Manage and notify upcoming tracking expirations": ["Manage and notify upcoming tracking expirations", "គ្រប់គ្រង និងជូនដំណឹងអំពីការផុតកំណត់សេវា GPS ដែលជិតមកដល់"],
    "Current client list": ["Current client list", "បញ្ជីអតិថិជនបច្ចុប្បន្ន"], "No file loaded": ["No file loaded", "មិនទាន់មានឯកសារ"],
    "Download the Excel template (the 7 required columns)": ["Download the Excel template (the 7 required columns)", "ទាញយកគំរូ Excel (ជួរឈរចាំបាច់ទាំង 7)"],
    "Download Excel template": ["Download Excel template", "ទាញយកគំរូ Excel"],
    "Add the rows of a new file to the current list (duplicate IMEI are skipped)": ["Add the rows of a new file to the current list (duplicate IMEI are skipped)", "បន្ថែមជួរពីឯកសារថ្មីទៅបញ្ជីបច្ចុប្បន្ន (IMEI ស្ទួនត្រូវរំលង)"],
    "Browse file": ["Browse file", "ជ្រើសឯកសារ"],
    "Replace the whole current list with a new file": ["Replace the whole current list with a new file", "ជំនួសបញ្ជីទាំងមូលដោយឯកសារថ្មី"], "Replace all": ["Replace all", "ជំនួសទាំងអស់"],
    "Toggle dark / light": ["Toggle dark / light", "ប្តូរងងឹត / ភ្លឺ"], "Signed in": ["Signed in", "បានចូលប្រើ"],
    "Sign out": ["Sign out", "ចាកចេញ"], "Language": ["Language", "ភាសា"], "Main": ["Main", "ម៉ឺនុយ"],
    "Sending…": ["Sending…", "កំពុងផ្ញើ…"],
    // ---- stat cards / overview / settings ----
    "ឧបករណ៍សរុប": ["Total units", "ឧបករណ៍សរុប"], "clients ·": ["clients ·", "អតិថិជន ·"], "paid off ·": ["paid off ·", "បង់ផ្តាច់ ·"], "rental": ["rental", "ជួល"],
    "មិនទាន់ដល់ពេល · Safe ≥ 30": ["Safe ≥ 30", "មិនទាន់ដល់ពេល ≥ 30"], "ថ្ងៃនៅសល់ ≥ 30": ["days left ≥ 30", "ថ្ងៃនៅសល់ ≥ 30"],
    "ជិតដល់ពេល · Approaching 7–29": ["Approaching 7–29", "ជិតដល់ពេល 7–29"], "ថ្ងៃនៅសល់ 7 ដល់ 29": ["days left 7 to 29", "ថ្ងៃនៅសល់ 7 ដល់ 29"],
    "ជិតផុត · Due ≤ 6": ["Due ≤ 6", "ជិតផុត ≤ 6"], "expired ·": ["expired ·", "ផុតកំណត់ ·"], "sent": ["sent", "បានផ្ញើ"],
    "ទិដ្ឋភាពទូទៅ": ["Expiry overview", "ទិដ្ឋភាពទូទៅ"], "Expiry overview": [X, X],
    "កំណត់": ["Settings", "ការកំណត់"], "Settings": [X, X],
    "Normal (ថ្ងៃ)": ["Normal (days)", "Normal (ថ្ងៃ)"], "Company (ថ្ងៃ)": ["Company (days)", "Company (ថ្ងៃ)"], "Rental (ថ្ងៃ)": ["Rental (days)", "Rental (ថ្ងៃ)"],
    "Max / run": ["Max / run", "អតិបរមា / ដង"], "Method": ["Method", "វិធីសាស្ត្រ"], "Telethon account": ["Telethon account", "គណនី Telethon"],
    "លេខទំនាក់ទំនងក្នុងសារ (Contact phone)": ["Contact phone (in the message)", "លេខទំនាក់ទំនងក្នុងសារ"],
    "ច្បាប់ផ្ញើ · Send rule:": ["Send rule:", "ច្បាប់ផ្ញើ៖"], "paid_off": ["paid_off", "បង់ផ្តាច់"],
    "→ Normal / Company days ·": ["→ Normal / Company days ·", "→ ចំនួនថ្ងៃ Normal / Company ·"], "→ Rental days (1 month). Ready to send now:": ["→ Rental days (1 month). Ready to send now:", "→ ចំនួនថ្ងៃ Rental (1 ខែ)។ ត្រៀមផ្ញើឥឡូវ៖"],
    "(+": ["(+", "(+"], "already sent)": ["already sent)", "បានផ្ញើរួច)"],
    // ---- toolbar / filters ----
    "ស្វែងរក Name (WL012), User, ស្លាកលេខ, IMEI…": ["Search Name (WL012), User, plate, IMEI…", "ស្វែងរក Name (WL012), User, ស្លាកលេខ, IMEI…"],
    "Filter": ["Filter", "តម្រង"], "ទាំងអស់ (All)": ["All", "ទាំងអស់"], "Safe ≥30": ["Safe ≥30", "មិនទាន់ដល់ពេល ≥30"],
    "Approaching 7–29": ["Approaching 7–29", "ជិតដល់ពេល 7–29"], "Due ≤6": ["Due ≤6", "ជិតផុត ≤6"], "ផុតកំណត់ (Expired)": ["Expired", "ផុតកំណត់"],
    "បានផ្ញើ (Sent)": ["Sent", "បានផ្ញើ"], "ត្រូវផ្ញើ (Ready)": ["Ready to send", "ត្រូវផ្ញើ"], "គ្មាន ID (No ID)": ["No ID", "គ្មាន ID"],
    "Days left": ["Days left", "ថ្ងៃនៅសល់"], "នៅសល់ (ថ្ងៃ):": ["Days left:", "នៅសល់ (ថ្ងៃ)៖"], "Days left from": ["Days left from", "ថ្ងៃនៅសល់ ពី"], "Days left to": ["Days left to", "ថ្ងៃនៅសល់ ដល់"],
    "User type": ["User type", "ប្រភេទអ្នកប្រើ"], "ប្រភេទអ្នកប្រើ · All": ["User type · All", "ប្រភេទអ្នកប្រើ · ទាំងអស់"], "Paid off": ["Paid off", "បង់ផ្តាច់"], "Rental": ["Rental", "ជួល"],
    "Apply one Username/ID to every plate with a Name": ["Apply one Username/ID to every plate with a Name", "ដាក់ Username/ID មួយទៅគ្រប់ស្លាកលេខដែលមាន Name ដូចគ្នា"],
    "បំពេញ ID · Fill Username/ID": ["Fill Username/ID", "បំពេញ Username/ID"], "More ▾": ["More ▾", "ច្រើនទៀត ▾"],
    "Set a new expiry date for the selected plates": ["Set a new expiry date for the selected plates", "កំណត់ថ្ងៃផុតកំណត់ថ្មីសម្រាប់ស្លាកលេខដែលបានជ្រើស"],
    "បន្តសេវា · Update expiry": ["Update expiry", "បន្តសេវា (ប្តូរថ្ងៃផុតកំណត់)"], "Select all": ["Select all", "ជ្រើសទាំងអស់"],
    // ---- table ----
    "USER / ID": ["USER / ID", "USER / ID"], "NAME": ["NAME", "ឈ្មោះ (NAME)"], "ប្រភេទ": ["TYPE", "ប្រភេទ"], "USER TYPE": ["USER TYPE", "ប្រភេទអ្នកប្រើ"],
    "ស្លាកលេខ": ["PLATE", "ស្លាកលេខ"], "ថ្ងៃផុតកំណត់": ["EXPIRY DATE", "ថ្ងៃផុតកំណត់"], "នៅសល់": ["DAYS LEFT", "នៅសល់"], "ស្ថានភាព": ["STATUS", "ស្ថានភាព"],
    "Required columns (first sheet, header in row 1):": ["Required columns (first sheet, header in row 1):", "ជួរឈរចាំបាច់ (សន្លឹកទីមួយ ក្បាលជួរនៅជួរទី 1)៖"],
    ". Optional:": [". Optional:", "។ ជម្រើស៖"], "(rental / paid_off, empty = paid_off),": ["(rental / paid_off, empty = paid_off),", "(rental / paid_off ទទេ = paid_off),"],
    "(e.g. WL112) and": ["(e.g. WL112) and", "(ឧ. WL112) និង"],
    "(Username/ID, can be filled in later on this page). Other columns are ignored. Browsing a new file ADDS its rows to the current list; a row whose IMEI already exists is skipped.":
      ["(Username/ID, can be filled in later on this page). Other columns are ignored. Browsing a new file ADDS its rows to the current list; a row whose IMEI already exists is skipped.",
       "(Username/ID អាចបំពេញនៅទំព័រនេះពេលក្រោយ)។ ជួរឈរផ្សេងត្រូវរំលង។ ការជ្រើសឯកសារថ្មី នឹងបន្ថែមជួរទៅបញ្ជីបច្ចុប្បន្ន ហើយជួរដែល IMEI មានរួចហើយត្រូវរំលង។"],
    "Download template": ["Download template", "ទាញយកគំរូ"], "Showing 0 results": ["Showing 0 results", "បង្ហាញ 0 លទ្ធផល"],
    "Select all matching": ["Select all matching", "ជ្រើសទាំងអស់ដែលត្រូវគ្នា"], "Clear selection": ["Clear selection", "លុបការជ្រើស"],
    "Rows per page": ["Rows per page", "ជួរក្នុងមួយទំព័រ"], "Previous page": ["Previous page", "ទំព័រមុន"], "Next page": ["Next page", "ទំព័របន្ទាប់"],
    "សារ (Message template)": ["Message template", "ទម្រង់សារ"], "Sent under the table image. Placeholders: {user} {count} {expiry_date} {phone}": ["Sent under the table image. Placeholders: {user} {count} {expiry_date} {phone}", "ផ្ញើក្រោមរូបតារាង។ អថេរ៖ {user} {count} {expiry_date} {phone}"],
    "កំណត់ត្រា (Activity log)": ["Activity log", "កំណត់ត្រាសកម្មភាព"],
    // ---- report ----
    "ព្យាយាមផ្ញើសរុប": ["Total attempts", "ព្យាយាមផ្ញើសរុប"], "Total attempts": [X, X], "ជោគជ័យ": ["Success", "ជោគជ័យ"], "បរាជ័យ": ["Failed", "បរាជ័យ"],
    "Failed · reason below": ["Failed · reason below", "បរាជ័យ · មូលហេតុនៅខាងក្រោម"], "មិនបានផ្ញើ": ["Skipped", "មិនបានផ្ញើ"], "Skipped (batch stopped)": ["Skipped (batch stopped)", "រំលង (ការផ្ញើត្រូវបានបញ្ឈប់)"],
    "ពីថ្ងៃ": ["From", "ពីថ្ងៃ"], "ដល់ថ្ងៃ": ["To", "ដល់ថ្ងៃ"], "Quick range": ["Quick range", "ជួរពេលរហ័ស"], "Today": ["Today", "ថ្ងៃនេះ"], "7 days": ["7 days", "7 ថ្ងៃ"], "30 days": ["30 days", "30 ថ្ងៃ"],
    "All": ["All", "ទាំងអស់"], "Report status": ["Report status", "ស្ថានភាពរបាយការណ៍"], "ជោគជ័យ (Success)": ["Success", "ជោគជ័យ"], "បរាជ័យ (Failed)": ["Failed", "បរាជ័យ"],
    "Skipped": ["Skipped", "រំលង"], "IMEI…": ["IMEI…", "IMEI…"], "User / Name…": ["User / Name…", "User / ឈ្មោះ…"], "Export report": ["Export report", "ទាញយករបាយការណ៍"],
    "លទ្ធផលតាមថ្ងៃ": ["Daily results", "លទ្ធផលតាមថ្ងៃ"], "Daily results": [X, X], "Success": ["Success", "ជោគជ័យ"], "Failed": ["Failed", "បរាជ័យ"],
    "No sends in this period.": ["No sends in this period.", "គ្មានការផ្ញើក្នុងអំឡុងពេលនេះទេ។"],
    "ទិន្នន័យមេ (Master)": ["Master", "ទិន្នន័យមេ"], "· one line per send · press Detail to see the plates": ["· one line per send · press Detail to see the plates", "· មួយជួរក្នុងមួយការផ្ញើ · ចុច Detail ដើម្បីមើលស្លាកលេខ"],
    "ថ្ងៃ (Date)": ["Date", "កាលបរិច្ឆេទ"], "Type": ["Type", "ប្រភេទ"], "Period": ["Period", "រយៈពេល"], "(ថ្ងៃនៅសល់)": ["(days left)", "(ថ្ងៃនៅសល់)"],
    "Message Sent": ["Message Sent", "សារដែលបានផ្ញើ"], "(Plate Expire)": ["(Plate Expire)", "(ស្លាកលេខផុតកំណត់)"], "Client": ["Client", "អតិថិជន"], "(Count)": ["(Count)", "(ចំនួន)"],
    "No sends for this filter.": ["No sends for this filter.", "គ្មានការផ្ញើតាមតម្រងនេះទេ។"], "Showing": ["Showing", "បង្ហាញ"], "sends": ["sends", "ការផ្ញើ"],
    "តាមថ្ងៃ (By day)": ["By day", "តាមថ្ងៃ"], "· click a day to see its details": ["· click a day to see its details", "· ចុចលើថ្ងៃដើម្បីមើលលម្អិត"], "សរុប": ["Total", "សរុប"], "% Success": ["% Success", "% ជោគជ័យ"],
    "ការកែប្រែដោយ Admin (Changes)": ["Admin changes", "ការកែប្រែដោយ Admin"], "· same date range · also in Export report": ["· same date range · also in Export report", "· ជួរថ្ងៃដូចគ្នា · មានក្នុងការទាញយករបាយការណ៍ដែរ"],
    "Change type": ["Change type", "ប្រភេទការកែប្រែ"], "ថ្ងៃផុតកំណត់ (Expiry)": ["Expiry date", "ថ្ងៃផុតកំណត់"], "Username/ID": ["Username/ID", "Username/ID"], "Import": ["Import", "នាំចូល"],
    "Name, plate, admin…": ["Name, plate, admin…", "ឈ្មោះ ស្លាកលេខ admin…"], "ពេលវេលា": ["Time", "ពេលវេលា"], "Admin": ["Admin", "Admin"], "សកម្មភាព": ["Action", "សកម្មភាព"],
    "ចំនួន (Plates)": ["Plates", "ចំនួនស្លាកលេខ"], "ការផ្លាស់ប្តូរ (Change)": ["Change", "ការផ្លាស់ប្តូរ"], "No changes in this period.": ["No changes in this period.", "គ្មានការកែប្រែក្នុងអំឡុងពេលនេះទេ។"], "changes": ["changes", "ការកែប្រែ"],
    "លម្អិតក្នុងមួយ Client (Per-client attempts & failure reasons)": ["Per-client attempts & failure reasons", "លម្អិតក្នុងមួយអតិថិជន (ការព្យាយាម និងមូលហេតុបរាជ័យ)"],
    "ឧបករណ៍": ["UNITS", "ឧបករណ៍"], "មូលហេតុ (Reason)": ["Reason", "មូលហេតុ"], "ផ្ញើដោយ": ["Sent by", "ផ្ញើដោយ"], "No report entries for this filter.": ["No report entries for this filter.", "គ្មានទិន្នន័យរបាយការណ៍តាមតម្រងនេះទេ។"], "entries": ["entries", "ធាតុ"],
    // ---- users ----
    "Admin login users": ["Admin login users", "អ្នកប្រើដែលអាចចូលប្រព័ន្ធ"], "People who can sign in and send reminders.": ["People who can sign in and send reminders.", "អ្នកដែលអាចចូលប្រព័ន្ធ និងផ្ញើការរំលឹក។"], "Add user": ["Add user", "បន្ថែមអ្នកប្រើ"],
    "Username": ["Username", "ឈ្មោះអ្នកប្រើ"], "សិទ្ធិ (Permissions)": ["Permissions", "សិទ្ធិ"], "បង្កើតនៅ": ["Created", "បង្កើតនៅ"], "ចូលចុងក្រោយ": ["Last sign-in", "ចូលចុងក្រោយ"],
    // ---- dock ----
    "Ready to process": ["Ready to process", "ត្រៀមដំណើរការ"], "View report": ["View report", "មើលរបាយការណ៍"], "Send again even if already marked Sent": ["Send again even if already marked Sent", "ផ្ញើម្តងទៀតទោះបីបានចំណាំថាផ្ញើរួចក៏ដោយ"],
    "បង្ខំផ្ញើម្តងទៀត": ["Force resend", "បង្ខំផ្ញើម្តងទៀត"], "Force resend": [X, X], "Preview": ["Preview", "មើលជាមុន"], "Export": ["Export", "ទាញយក"], "Stop": ["Stop", "បញ្ឈប់"],
    "ផ្ញើអ្នកដែលបានជ្រើស": ["Send selected", "ផ្ញើអ្នកដែលបានជ្រើស"], "ផ្ញើ": ["Send", "ផ្ញើ"], "Send all due": ["all due", "ទាំងអស់ដែលដល់ពេល"],
    // ---- dialogs ----
    "Password (10+ characters)": ["Password (10+ characters)", "ពាក្យសម្ងាត់ (10 តួឡើង)"], "សិទ្ធិ · Permissions": ["Permissions", "សិទ្ធិ"],
    "មើល Report": ["View report", "មើលរបាយការណ៍"], "View report & changes": ["View report & changes", "មើលរបាយការណ៍ និងការកែប្រែ"], "Import file": ["Import file", "នាំចូលឯកសារ"], "Browse / Replace all": ["Browse / Replace all", "ជ្រើស / ជំនួសទាំងអស់"],
    "ផ្ញើសារ": ["Send messages", "ផ្ញើសារ"], "Preview, Send, Stop": ["Preview, Send, Stop", "មើលជាមុន ផ្ញើ បញ្ឈប់"], "បន្តសេវា": ["Update expiry", "បន្តសេវា"], "Update expiry date": ["Update expiry date", "ប្តូរថ្ងៃផុតកំណត់"],
    "បំពេញ ID": ["Fill ID", "បំពេញ ID"], "Fill Username/ID": ["Fill Username/ID", "បំពេញ Username/ID"], "Dashboard & Report to Excel": ["Dashboard & Report to Excel", "ទាញយក Dashboard និង Report ជា Excel"],
    "Manage users & permissions": ["Manage users & permissions", "គ្រប់គ្រងអ្នកប្រើ និងសិទ្ធិ"], "Save": ["Save", "រក្សាទុក"], "Cancel": ["Cancel", "បោះបង់"],
    "បន្តសេវា · Update expiry date": ["Update expiry date", "បន្តសេវា · ប្តូរថ្ងៃផុតកំណត់"], "ថ្ងៃផុតកំណត់ថ្មី · New expiry date": ["New expiry date", "ថ្ងៃផុតកំណត់ថ្មី"],
    "The customer renewed: \"Sent\" is cleared, so these plates show again (Approaching / Due) when the new date gets close.": ["The customer renewed: \"Sent\" is cleared, so these plates show again (Approaching / Due) when the new date gets close.", "អតិថិជនបានបន្តសេវា៖ ស្ថានភាព \"Sent\" ត្រូវលុប ដូច្នេះស្លាកលេខទាំងនេះនឹងបង្ហាញម្តងទៀត (ជិតដល់ពេល / ជិតផុត) ពេលថ្ងៃថ្មីជិតមកដល់។"],
    "Update": ["Update", "កែ"], "បំពេញ Username/ID · Fill by Name": ["Fill Username/ID by Name", "បំពេញ Username/ID តាម Name"], "Name (e.g. WL012)": ["Name (e.g. WL012)", "Name (ឧ. WL012)"],
    "ចុចដើម្បីជ្រើស Name ដែលមិនទាន់មាន ID": ["Click to pick a Name that has no ID yet", "ចុចដើម្បីជ្រើស Name ដែលមិនទាន់មាន ID"],
    "បង្ហាញ Name ដែលមាន ID រួច (ដើម្បីប្តូរ ID) · also list Names that already have an ID": ["Also list Names that already have an ID (to change it)", "បង្ហាញ Name ដែលមាន ID រួចផង (ដើម្បីប្តូរ ID)"],
    "Type a Name. Every plate with this Name gets the Username/ID.": ["Type a Name. Every plate with this Name gets the Username/ID.", "វាយ Name។ គ្រប់ស្លាកលេខដែលមាន Name នេះនឹងទទួលបាន Username/ID។"],
    "Username / ID": ["Username / ID", "Username / ID"], "@username or 123456789": ["@username or 123456789", "@username ឬ 123456789"], "Apply to all": ["Apply to all", "អនុវត្តទាំងអស់"],
    "Detail": ["Detail", "លម្អិត"], "Detail Paid Off": ["Detail Paid Off", "លម្អិត បង់ផ្តាច់ (Paid Off)"], "User (Name)": ["User (Name)", "User (ឈ្មោះ)"], "Plate Number": ["Plate Number", "ស្លាកលេខ"],
    "Expire Date": ["Expire Date", "ថ្ងៃផុតកំណត់"], "Status": ["Status", "ស្ថានភាព"], "None": ["None", "គ្មាន"], "Detail Rental": ["Detail Rental", "លម្អិត ជួល (Rental)"], "Close": ["Close", "បិទ"],
    "Change detail": ["Change detail", "លម្អិតការកែប្រែ"], "Plate": ["Plate", "ស្លាកលេខ"], "មុន (Old)": ["Old", "មុន"], "ក្រោយ (New)": ["New", "ក្រោយ"], "Message preview": ["Message preview", "មើលសារជាមុន"],
    // ---- login page ----
    "Sign in · GPS Expiry Notifier": ["Sign in · GPS Expiry Notifier", "ចូលប្រើ · ប្រព័ន្ធជូនដំណឹង GPS ផុតកំណត់"], "GPS Expiry": ["GPS Expiry", "GPS Expiry"],
    "ជូនដំណឹងអតិថិជនមុនសេវា GPS ផុតកំណត់": ["Notify clients before their GPS service expires", "ជូនដំណឹងអតិថិជនមុនសេវា GPS ផុតកំណត់"],
    "Send renewal reminders to every client in one message, with a clear table of their units.": ["Send renewal reminders to every client in one message, with a clear table of their units.", "ផ្ញើការរំលឹកបន្តសេវាទៅអតិថិជននីមួយៗក្នុងសារតែមួយ ជាមួយតារាងឧបករណ៍ច្បាស់លាស់។"],
    "One message per client, all units in one table": ["One message per client, all units in one table", "សារមួយក្នុងមួយអតិថិជន ឧបករណ៍ទាំងអស់ក្នុងតារាងតែមួយ"],
    "Daily report with success and failure reasons": ["Daily report with success and failure reasons", "របាយការណ៍ប្រចាំថ្ងៃ ជាមួយមូលហេតុជោគជ័យ និងបរាជ័យ"], "Built for thousands of units": ["Built for thousands of units", "បង្កើតសម្រាប់ឧបករណ៍រាប់ពាន់"],
    "Welcome back": ["Welcome back", "សូមស្វាគមន៍"], "Sign in to continue.": ["Sign in to continue.", "សូមចូលប្រើដើម្បីបន្ត។"], "Password": ["Password", "ពាក្យសម្ងាត់"], "Sign in": ["Sign in", "ចូលប្រើ"],
    "Show password": ["Show password", "បង្ហាញពាក្យសម្ងាត់"], "Hide password": ["Hide password", "លាក់ពាក្យសម្ងាត់"],
    // ---- messages made by app.js / server (English key -> English, Khmer) ----
    "Wrong username or password.": ["Wrong username or password.", "ឈ្មោះអ្នកប្រើ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ។"],
    "Too many attempts. Try again in {n} minute(s).": ["Too many attempts. Try again in {n} minute(s).", "ព្យាយាមច្រើនដងពេក។ សូមព្យាយាមម្តងទៀតក្នុងរយៈពេល {n} នាទី។"],
    "Not signed in": ["Not signed in", "មិនទាន់បានចូលប្រើ"],
    "You do not have permission for this. Ask an admin. / អ្នកគ្មានសិទ្ធិធ្វើសកម្មភាពនេះទេ។": ["You do not have permission for this. Ask an admin.", "អ្នកគ្មានសិទ្ធិធ្វើសកម្មភាពនេះទេ។ សូមសួរ admin។"],
    "Request failed (HTTP {n}) - server not responding or restarted": ["Request failed (HTTP {n}) - server not responding or restarted", "សំណើបរាជ័យ (HTTP {n}) - ម៉ាស៊ីនមេមិនឆ្លើយតប ឬកំពុង restart"],
    "Select at least one row first.": ["Select at least one row first.", "សូមជ្រើសយ៉ាងតិចមួយជួរជាមុន។"],
    "Selected units are already Sent. Turn on Force resend to send again.": ["Selected units are already Sent. Turn on Force resend to send again.", "ឧបករណ៍ដែលបានជ្រើសបានផ្ញើរួចហើយ។ បើក \"បង្ខំផ្ញើម្តងទៀត\" ដើម្បីផ្ញើម្តងទៀត។"],
    "No clients are due right now.": ["No clients are due right now.", "បច្ចុប្បន្នគ្មានអតិថិជនដែលដល់ពេលផ្ញើទេ។"],
    "FORCE RESEND is ON: {n} unit(s) will be sent, including ones already sent before. Continue?": ["FORCE RESEND is ON: {n} unit(s) will be sent, including ones already sent before. Continue?", "បង្ខំផ្ញើម្តងទៀតកំពុងបើក៖ នឹងផ្ញើ {n} ឧបករណ៍ រួមទាំងឧបករណ៍ដែលបានផ្ញើរួច។ បន្តទេ?"],
    "Send reminders for {n} unit(s)? (one message per client; units already Sent are skipped)": ["Send reminders for {n} unit(s)? (one message per client; units already Sent are skipped)", "ផ្ញើការរំលឹកសម្រាប់ {n} ឧបករណ៍? (សារមួយក្នុងមួយអតិថិជន; ឧបករណ៍ដែលបានផ្ញើរួចត្រូវរំលង)"],
    "Started: {n} client message(s) queued.": ["Started: {n} client message(s) queued.", "ចាប់ផ្តើម៖ សារ {n} ដល់អតិថិជនកំពុងរង់ចាំផ្ញើ។"], " (force resend)": [" (force resend)", " (បង្ខំផ្ញើម្តងទៀត)"],
    "{n} plate(s) skipped, no Username/ID: {names}. Use \"Fill Username/ID\".": ["{n} plate(s) skipped, no Username/ID: {names}. Use \"Fill Username/ID\".", "រំលង {n} ស្លាកលេខ គ្មាន Username/ID៖ {names}។ សូមប្រើ \"បំពេញ Username/ID\"។"],
    "Sending {done}/{total}": ["Sending {done}/{total}", "កំពុងផ្ញើ {done}/{total}"],
    "Sending {done} of {total} clients · {sent} sent, {failed} failed": ["Sending {done} of {total} clients · {sent} sent, {failed} failed", "កំពុងផ្ញើ {done} ក្នុងចំណោម {total} អតិថិជន · ជោគជ័យ {sent} បរាជ័យ {failed}"],
    "Done · sent {sent}, failed {failed}": ["Done · sent {sent}, failed {failed}", "ចប់ · ជោគជ័យ {sent} បរាជ័យ {failed}"],
    "No clients match your search or filter.": ["No clients match your search or filter.", "គ្មានអតិថិជនត្រូវនឹងការស្វែងរក ឬតម្រងរបស់អ្នកទេ។"],
    "No file loaded yet. Browse for an Excel file, or drag one onto this page.": ["No file loaded yet. Browse for an Excel file, or drag one onto this page.", "មិនទាន់មានឯកសារទេ។ សូមជ្រើសឯកសារ Excel ឬអូសមកដាក់ក្នុងទំព័រនេះ។"],
    "Showing {from}–{to} of {total} results": ["Showing {from}–{to} of {total} results", "បង្ហាញ {from}–{to} ក្នុងចំណោម {total} លទ្ធផល"],
    "{n} selected": ["{n} selected", "បានជ្រើស {n}"], "{n} units selected.": ["{n} units selected.", "បានជ្រើស {n} ឧបករណ៍។"], "units": ["units", "ឧបករណ៍"],
    "{n} days": ["{n} days", "{n} ថ្ងៃ"], "No ID": ["No ID", "គ្មាន ID"],
    "Days left {lo}–{hi}: {n} unit(s)": ["Days left {lo}–{hi}: {n} unit(s)", "នៅសល់ {lo}–{hi} ថ្ងៃ៖ {n} គ្រឿង"],
    "To: {user} · {units} unit(s) · {images} image(s), the message goes with the last image": ["To: {user} · {units} unit(s) · {images} image(s), the message goes with the last image", "ទៅ៖ {user} · {units} ឧបករណ៍ · {images} រូប សារនឹងផ្ញើជាមួយរូបចុងក្រោយ"],
    " · table image unavailable (text list will be sent)": [" · table image unavailable (text list will be sent)", " · រូបតារាងមិនអាចប្រើបាន (នឹងផ្ញើជាបញ្ជីអក្សរ)"],
    "Add the new rows from \"{f}\" to the current list?\nRows whose IMEI already exists are skipped.": ["Add the new rows from \"{f}\" to the current list?\nRows whose IMEI already exists are skipped.", "បន្ថែមជួរថ្មីពី \"{f}\" ទៅបញ្ជីបច្ចុប្បន្ន?\nជួរដែល IMEI មានរួចហើយត្រូវរំលង។"],
    "REPLACE the whole client list with \"{f}\"? The old data will be removed.": ["REPLACE the whole client list with \"{f}\"? The old data will be removed.", "ជំនួសបញ្ជីអតិថិជនទាំងមូលដោយ \"{f}\"? ទិន្នន័យចាស់នឹងត្រូវលុប។"],
    "Importing…": ["Importing…", "កំពុងនាំចូល…"],
    " Skipped {n} duplicate IMEI ({list}).": [" Skipped {n} duplicate IMEI ({list}).", " បានរំលង IMEI ស្ទួន {n} ({list})។"],
    " Skipped {n} row(s) without IMEI.": [" Skipped {n} row(s) without IMEI.", " បានរំលង {n} ជួរដែលគ្មាន IMEI។"], " But: {w}.": [" But: {w}.", " ប៉ុន្តែ៖ {w}។"],
    "Added {n} new row(s) of {total}.": ["Added {n} new row(s) of {total}.", "បានបន្ថែម {n} ជួរថ្មី ក្នុងចំណោម {total}។"],
    "Imported {n} row(s) from {f}, but: {w}. Fix them in Excel and import again.": ["Imported {n} row(s) from {f}, but: {w}. Fix them in Excel and import again.", "បាននាំចូល {n} ជួរពី {f} ប៉ុន្តែ៖ {w}។ សូមកែក្នុង Excel ហើយនាំចូលម្តងទៀត។"],
    "Imported {n} row(s) from {f}.": ["Imported {n} row(s) from {f}.", "បាននាំចូល {n} ជួរពី {f}។"],
    "Select plates first (search a Name such as WL012, then 'Select all matching').": ["Select plates first (search a Name such as WL012, then 'Select all matching').", "សូមជ្រើសស្លាកលេខជាមុន (ស្វែងរក Name ដូចជា WL012 រួចចុច 'ជ្រើសទាំងអស់ដែលត្រូវគ្នា')។"],
    "{n} plate(s) selected.": ["{n} plate(s) selected.", "បានជ្រើស {n} ស្លាកលេខ។"], "Choose the new expiry date.": ["Choose the new expiry date.", "សូមជ្រើសថ្ងៃផុតកំណត់ថ្មី។"],
    "New expiry date {d} saved on {n} plate(s).": ["New expiry date {d} saved on {n} plate(s).", "បានរក្សាទុកថ្ងៃផុតកំណត់ថ្មី {d} លើ {n} ស្លាកលេខ។"],
    "ID: {ids}": ["ID: {ids}", "ID៖ {ids}"], "{n} plate(s) · no ID": ["{n} plate(s) · no ID", "{n} ស្លាកលេខ · គ្មាន ID"], "{n} Name": ["{n} Name", "{n} Name"],
    "Current ID: {ids} · {w}/{p} plate(s). Typing a new ID below will CHANGE it.": ["Current ID: {ids} · {w}/{p} plate(s). Typing a new ID below will CHANGE it.", "ID បច្ចុប្បន្ន៖ {ids} · {w}/{p} ស្លាកលេខ។ ការវាយ ID ថ្មីខាងក្រោមនឹងប្តូរវា។"],
    "{p} plate(s) have this Name, none has a Username/ID yet.": ["{p} plate(s) have this Name, none has a Username/ID yet.", "{p} ស្លាកលេខមាន Name នេះ ហើយមិនទាន់មាន Username/ID ទេ។"], "old: {id}": ["old: {id}", "ចាស់៖ {id}"],
    "Enter the Name and the Username/ID.": ["Enter the Name and the Username/ID.", "សូមបញ្ចូល Name និង Username/ID។"],
    "{name} already has the Username/ID {ids}.\nChange it to {user} on all {p} plate(s)?": ["{name} already has the Username/ID {ids}.\nChange it to {user} on all {p} plate(s)?", "{name} មាន Username/ID {ids} រួចហើយ។\nប្តូរទៅ {user} លើទាំង {p} ស្លាកលេខឬ?"],
    "Username/ID {user} applied to {n} plate(s) named {name}.": ["Username/ID {user} applied to {n} plate(s) named {name}.", "បានដាក់ Username/ID {user} លើ {n} ស្លាកលេខឈ្មោះ {name}។"],
    "Daily send results, successes and failures": ["Daily send results, successes and failures", "លទ្ធផលផ្ញើប្រចាំថ្ងៃ ជោគជ័យ និងបរាជ័យ"], "Admin accounts that can sign in": ["Admin accounts that can sign in", "គណនីអ្នកគ្រប់គ្រងដែលអាចចូលប្រើ"],
    "Report keeps the last 3 months (from {d}); older days are removed automatically.": ["Report keeps the last 3 months (from {d}); older days are removed automatically.", "របាយការណ៍រក្សាទុក 3 ខែចុងក្រោយ (ចាប់ពី {d}); ថ្ងៃចាស់ជាងនេះត្រូវលុបដោយស្វ័យប្រវត្តិ។"],
    "{n}% success": ["{n}% success", "{n}% ជោគជ័យ"], "Show this day": ["Show this day", "បង្ហាញថ្ងៃនេះ"],
    "{day}: {s} success, {f} failed, {k} skipped": ["{day}: {s} success, {f} failed, {k} skipped", "{day}៖ ជោគជ័យ {s} បរាជ័យ {f} រំលង {k}"],
    "{n} fail": ["{n} fail", "បរាជ័យ {n}"], "{n} skipped": ["{n} skipped", "រំលង {n}"], "Auto": ["Auto", "ស្វ័យប្រវត្តិ"], "Manual": ["Manual", "ដោយដៃ"],
    "· Client (Count): {c} · {n} plate(s)": ["· Client (Count): {c} · {n} plate(s)", "· ចំនួនអតិថិជន (Client Count)៖ {c} · {n} ស្លាកលេខ"],
    "Detail · {ts} · {kind}": ["Detail · {ts} · {kind}", "លម្អិត · {ts} · {kind}"], "Period {p} days · {s} sent · {c} client(s)": ["Period {p} days · {s} sent · {c} client(s)", "រយៈពេល {p} ថ្ងៃ · បានផ្ញើ {s} · {c} អតិថិជន"],
    "Admin: {a} · {n} item(s)": ["Admin: {a} · {n} item(s)", "Admin៖ {a} · {n} ធាតុ"],
    "ថ្ងៃផុតកំណត់ (Expiry date)": ["Expiry date", "ថ្ងៃផុតកំណត់"],
    "Main admin · all": ["Main admin · all", "Admin ចម្បង · ទាំងអស់"], "— none —": ["— none —", "— គ្មាន —"], "Disable": ["Disable", "បិទ"], "Enable": ["Enable", "បើក"], "Delete": ["Delete", "លុប"],
    "Reset password": ["Reset password", "កំណត់ពាក្យសម្ងាត់ឡើងវិញ"], "Permissions": ["Permissions", "សិទ្ធិ"], "Delete user \"{u}\"?": ["Delete user \"{u}\"?", "លុបអ្នកប្រើ \"{u}\" ?"],
    "(you)": ["(you)", "(អ្នក)"], "Active": ["Active", "សកម្ម"], "Disabled": ["Disabled", "បិទ"],
    "Permissions: {u}": ["Permissions: {u}", "សិទ្ធិ៖ {u}"], "Reset password: {u}": ["Reset password: {u}", "កំណត់ពាក្យសម្ងាត់ឡើងវិញ៖ {u}"],
    "User created.": ["User created.", "បានបង្កើតអ្នកប្រើ។"], "Permissions saved.": ["Permissions saved.", "បានរក្សាទុកសិទ្ធិ។"], "Password changed.": ["Password changed.", "បានប្តូរពាក្យសម្ងាត់។"],
    "perm.report": ["Report", "របាយការណ៍"], "perm.import": ["Import", "នាំចូល"], "perm.send": ["Send", "ផ្ញើ"], "perm.expiry": ["Expiry", "ថ្ងៃផុតកំណត់"], "perm.fill_id": ["Fill ID", "បំពេញ ID"], "perm.export": ["Export", "ទាញយក"], "perm.users": ["Admin", "Admin"],
    "Username/ID filled": ["Username/ID filled", "បានបំពេញ Username/ID"], "File imported": ["File imported", "បាននាំចូលឯកសារ"],
    // dashboard status words (STATUS / RSTATUS)
    "st.safe": ["Safe", "មិនទាន់ដល់ពេល"], "st.approaching": ["Approaching", "ជិតដល់ពេល"], "st.due": ["Due", "ជិតផុត"], "st.expired": ["Expired", "ផុតកំណត់"], "st.sent": ["Sent", "បានផ្ញើ"], "st.invalid": ["Invalid date", "កាលបរិច្ឆេទមិនត្រឹមត្រូវ"],
    "rs.sent": ["Success", "ជោគជ័យ"], "rs.failed": ["Failed", "បរាជ័យ"], "rs.skipped": ["Skipped", "រំលង"],
    "SEG.safe": ["Safe ≥ 30", "មិនទាន់ដល់ពេល ≥ 30"], "SEG.approaching": ["Approaching 7–29", "ជិតដល់ពេល 7–29"], "SEG.due": ["Due ≤ 6", "ជិតផុត ≤ 6"], "SEG.expired": ["Expired", "ផុតកំណត់"], "SEG.sent": ["Sent", "បានផ្ញើ"],
    // server messages (exact English texts from app.py)
    "Choose a valid expiry date.": ["Choose a valid expiry date.", "សូមជ្រើសថ្ងៃផុតកំណត់ដែលត្រឹមត្រូវ។"], "Select at least one plate first.": ["Select at least one plate first.", "សូមជ្រើសយ៉ាងតិចមួយស្លាកលេខជាមុន។"],
    "Wait for the running batch to finish.": ["Wait for the running batch to finish.", "សូមរង់ចាំការផ្ញើដែលកំពុងដំណើរការឱ្យចប់សិន។"], "A batch is already running.": ["A batch is already running.", "មានការផ្ញើកំពុងដំណើរការរួចហើយ។"],
    "The message template is empty.": ["The message template is empty.", "ទម្រង់សារគឺទទេ។"], "Username/ID is not valid. Use @username (5-32 letters, digits, _) or a numeric Telegram ID.": ["Username/ID is not valid. Use @username (5-32 letters, digits, _) or a numeric Telegram ID.", "Username/ID មិនត្រឹមត្រូវ។ សូមប្រើ @username (5-32 តួអក្សរ លេខ _) ឬលេខ Telegram ID។"],
    "No matching rows to preview.": ["No matching rows to preview.", "គ្មានជួរត្រូវគ្នាសម្រាប់មើលជាមុនទេ។"], "Please choose an Excel (.xlsx, .xlsm) or .csv file.": ["Please choose an Excel (.xlsx, .xlsm) or .csv file.", "សូមជ្រើសឯកសារ Excel (.xlsx, .xlsm) ឬ .csv។"],
    "This is not a real Excel (.xlsx) file.": ["This is not a real Excel (.xlsx) file.", "នេះមិនមែនជាឯកសារ Excel (.xlsx) ពិតប្រាកដទេ។"], "This is not a real CSV text file.": ["This is not a real CSV text file.", "នេះមិនមែនជាឯកសារ CSV អក្សរពិតប្រាកដទេ។"],
    "File too large (maximum 10 MB).": ["File too large (maximum 10 MB).", "ឯកសារធំពេក (អតិបរមា 10 MB)។"], "Request rejected. Refresh the page (Ctrl+F5) and try again.": ["Request rejected. Refresh the page (Ctrl+F5) and try again.", "សំណើត្រូវបានបដិសេធ។ សូម Refresh ទំព័រ (Ctrl+F5) ហើយព្យាយាមម្តងទៀត។"],
    "Username: 3-32 characters, letters, numbers, . _ - only.": ["Username: 3-32 characters, letters, numbers, . _ - only.", "ឈ្មោះអ្នកប្រើ៖ 3-32 តួ អក្សរ លេខ . _ - ប៉ុណ្ណោះ។"], "That username already exists.": ["That username already exists.", "ឈ្មោះអ្នកប្រើនេះមានរួចហើយ។"],
    "Password must be 10-128 characters.": ["Password must be 10-128 characters.", "ពាក្យសម្ងាត់ត្រូវមាន 10-128 តួ។"], "Password must not contain the username.": ["Password must not contain the username.", "ពាក្យសម្ងាត់មិនត្រូវមានឈ្មោះអ្នកប្រើទេ។"],
    "Password is too easy to guess. Mix letters, numbers and symbols.": ["Password is too easy to guess. Mix letters, numbers and symbols.", "ពាក្យសម្ងាត់ងាយទាយពេក។ សូមលាយអក្សរ លេខ និងសញ្ញា។"],
    "Only the main admin can change this account.": ["Only the main admin can change this account.", "មានតែ Admin ចម្បងប៉ុណ្ណោះដែលអាចកែគណនីនេះ។"], "Only the main admin can make someone an Admin.": ["Only the main admin can make someone an Admin.", "មានតែ Admin ចម្បងប៉ុណ្ណោះដែលអាចតែងតាំង Admin។"],
    "Only the main admin can create another Admin.": ["Only the main admin can create another Admin.", "មានតែ Admin ចម្បងប៉ុណ្ណោះដែលអាចបង្កើត Admin ថ្មី។"], "You cannot remove your own 'manage users' permission.": ["You cannot remove your own 'manage users' permission.", "អ្នកមិនអាចដកសិទ្ធិគ្រប់គ្រងអ្នកប្រើរបស់ខ្លួនឯងបានទេ។"],
    "You cannot disable your own account.": ["You cannot disable your own account.", "អ្នកមិនអាចបិទគណនីខ្លួនឯងបានទេ។"], "You cannot delete your own account.": ["You cannot delete your own account.", "អ្នកមិនអាចលុបគណនីខ្លួនឯងបានទេ។"], "User not found.": ["User not found.", "រកមិនឃើញអ្នកប្រើទេ។"],
    "Name is empty.": ["Name is empty.", "Name ទទេ។"], "Server error. Try again; if it repeats check the server log.": ["Server error. Try again; if it repeats check the server log.", "កំហុសម៉ាស៊ីនមេ។ សូមព្យាយាមម្តងទៀត បើនៅតែកើតឡើងសូមពិនិត្យ server log។"],
    "Signed out: the password changed. Sign in again.": ["Signed out: the password changed. Sign in again.", "បានចាកចេញ៖ ពាក្យសម្ងាត់ត្រូវបានប្តូរ។ សូមចូលប្រើម្តងទៀត។"]
  };
  var TPL = []; // keys with {vars} -> RegExp, so server texts with numbers can be translated too
  Object.keys(D).forEach(function (k) {
    if (k.indexOf("{") < 0) return;
    var names = [], re = k.replace(/[.*+?^$()|[\]\\]/g, "\\$&").replace(/\{(\w+)\}/g, function (_, n) { names.push(n); return "([\\s\\S]+?)"; });
    TPL.push({ key: k, re: new RegExp("^" + re + "$"), names: names });
  });
  var idx = lang === "km" ? 1 : 0;
  function fill(s, v) { return s.replace(/\{(\w+)\}/g, function (m, n) { return v && v[n] !== undefined ? v[n] : m; }); }
  function t(key, vars) {
    var e = D[key];
    if (e) return fill(e[idx], vars);
    if (!vars) {                                    // a finished sentence (e.g. from the server) that matches a template
      for (var i = 0; i < TPL.length; i++) {
        var m = TPL[i].re.exec(key);
        if (m) { var v = {}; TPL[i].names.forEach(function (n, j) { v[n] = m[j + 1]; }); return fill(D[TPL[i].key][idx], v); }
      }
    }
    return vars ? fill(key, vars) : key;
  }
  function norm(s) { return s.replace(/\s+/g, " ").trim(); }
  function apply(root) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { var p = n.parentNode && n.parentNode.nodeName; return /^(SCRIPT|STYLE)$/i.test(p) || !n.nodeValue.trim() ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
    }), nodes = [], n;
    while ((n = w.nextNode())) nodes.push(n);
    nodes.forEach(function (n) {
      var raw = n.nodeValue, key = norm(raw), out = t(key);
      if (out !== key) n.nodeValue = raw.replace(/^(\s*)[\s\S]*?(\s*)$/, function (_, a, b) { return a + out + b; });
    });
    root.querySelectorAll("[placeholder],[title],[aria-label]").forEach(function (e) {
      ["placeholder", "title", "aria-label"].forEach(function (a) { var v = e.getAttribute(a); if (v) { var o = t(norm(v)); if (o !== norm(v)) e.setAttribute(a, o); } });
    });
  }
  function set(l) { try { localStorage.setItem(KEY, l); } catch (e) { /* ignore */ } location.reload(); }
  function init() {
    document.documentElement.lang = lang;
    apply(document.documentElement);
    var b = document.getElementById("langBtn");
    if (b) { b.querySelector(".lang-lbl").textContent = lang === "km" ? "English" : "ខ្មែរ"; b.title = lang === "km" ? "Switch to English" : "ប្តូរទៅភាសាខ្មែរ"; b.addEventListener("click", function () { set(lang === "km" ? "en" : "km"); }); }
  }
  window.I18N = { t: t, lang: lang, apply: apply };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

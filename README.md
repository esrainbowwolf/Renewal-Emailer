Project Explanation:

This is code that takes in Syncro_Assets_mm_dd_yyyy.csv excel sheet.
This sheet mixes companies together so this separates them by the customer_business_name column into their own sheets.
The main one this is for is TechDoctors as we were watching renewal dates for these residential customers.
We had a Master excel sheet that contained TechDoctors customer information including renewal dates.
We would compare these renewal dates versus the current date to find renewals happening within 14 days.
The system would email support@testdomain.com with an excel sheet attachments of the renewals.
This would allow us to easily know who to contact for renewals

-----------

NOTE!!!

ALL DOCUMENTS USE TODAY'S DATE AS mm_dd_yyyy. If something is not run make sure those have been updated.

ALL DATA IS FAKE FOR THE SAKE OF DATA PROTECTION

-----------
Important Documents + explanation:

CSV_Manipulator.py | Reads main excel sheet, makes excel sheets, calls Emailer.py, run this to run program

Downloader.py | Not finished. Meant to automatically download files and format them

Emailer.py | Automatically sends an email so it creates a ticket with generic formatting and attachment excel sheet

Syncro_Assets_mm_dd_yyyy.csv | Main Dataset that the program uses
TechDoctors Master List - Covered by BTS.csv | Customers the business paid for automatically without customer payment

TechDoctors Master List - Monthly.csv | Customers that renewed Monthly

TechDoctors Master List - Yearly.csv | Customers that renewed Yearly

Run_GET_Renewals.bat | Meant for windows machines to automatically run the files certain

-----------

Things created by scripts:

Need_Fixed_TD.csv | Customers missing from the Syncro sheet or the Master sheet and notates which one is missing

Old_Renew_Soon.csv | Customers that are renewing as of last time program was ran

Renew_Soon.csv | Customers that are renewing soon

-----------

SETUP (This was done in Pycharm so the environment variable section may be different depending on IDE)


Code changes required:

CSV_Manipulator.py Line 21 | EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "ms") for Microsoft 365

CSV_Manipulator.py Line 21 | EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "google") for Gmail

CSV_Manipulator.py Line 228 | set the receiver email

CSV_Manipulator.py Line 233 | Set the sender email

Add protected environment variables with the services depending on which service is used to send email:

(Only for PyCharm. Please look up your Environement variables for your specific IDE)

Run>Edit Configurations>Environment Variables:> Click "notepad"

Add: (MS if using Microsoft 365) (GOOGLE if using gmail)

Name                    Value

MS_TENANT_ID            "Directory (tenant) ID"

MS_CLIENT_ID            "Application (client) ID"

MS_CLIENT_SECRET        "Secret ID"

GOOGLE_PASS             "App Password"


Environment Variables should look like:

PYTHONUNBUFFERED=1;MS_TENANT_ID="Directory (tenant) ID";MS_CLIENT_ID="Application (client) ID";MS_CLIENT_SECRET="Secret ID";GOOGLE_PASS="App Password"

-----------
To Run:

Make sure to have updated Master list and have the updated Syncro Assets files with current date.

Run CSV_Manipulator.py

-----------

Missing Features:
Automated file downloading.
Automated system running
General GUI

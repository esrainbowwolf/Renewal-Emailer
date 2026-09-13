import pandas as pd
import os
import re


from datetime import date, datetime
from Emailer import send_email

TODAY_STR = date.today().strftime("%m_%d_%Y")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYNCRO_ASSETS_FILE = os.path.join(BASE_DIR, 'Data', f'Syncro_Assets_{TODAY_STR}.csv')
TECH_DOCTORS_MASTER_MONTHLY = os.path.join(BASE_DIR, 'Data', 'Tech Doctor Renewal Master List - Monthly.csv')
TECH_DOCTORS_MASTER_YEARLY = os.path.join(BASE_DIR, 'Data', 'Tech Doctor Renewal Master List - Yearly.csv')
TECH_DOCTORS_MASTER_COVERED = os.path.join(BASE_DIR, 'Data', 'Tech Doctor Renewal Master List - Covered by BTS.csv')
OLD_RENEW_SOON = os.path.join(BASE_DIR, 'Data', 'Renew_Soon.csv')

# Which email backend Emailer.send_email should use: "ms" or "google".
# Emailer.py reads its own credentials (MS_TENANT_ID/MS_CLIENT_ID/MS_CLIENT_SECRET
# or GOOGLE_PASS) based on whichever provider is selected here.
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "ms")


def load_csv(csv_file):
    df = pd.read_csv(csv_file)
    return df

def load_csv_if_exists(csv_file):
    """
    Like load_csv, but returns an empty DataFrame instead of raising
    if the file doesn't exist yet (e.g. first run before any output exists).
    """
    if os.path.exists(csv_file):
        return pd.read_csv(csv_file)
    return pd.DataFrame()

def make_csv(df, filename):
    safe_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)  # <-- sanitize first
    output_filename = f"{safe_filename}.csv"
    output_dir = os.path.join(BASE_DIR, 'Data')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    df.to_csv(output_path, index=False)
    print(f"Exported to: {output_path}")

def make_csv_w_date(df, filename):
    safe_filename = re.sub(r'[\\/*?:"<>|]', '_', filename)  # <-- sanitize first
    output_filename = f"{safe_filename}_{TODAY_STR}.csv"
    output_dir = os.path.join(BASE_DIR, 'Data', TODAY_STR)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)
    df.to_csv(output_path, index=False)
    print(f"Exported to: {output_path}")

def mass_update_csv(df):
    business_list = df['customer_business_name'].unique().tolist()
    for business in business_list:
        test_df = df[df['customer_business_name'] == business].copy()
        make_csv_w_date(test_df, business)

def calculate_days(date_one, date_two):
    return date_two - date_one

def strip_column(df, column):
    return df[column].copy()

def strip_column_data(df, column, data):
    return df[df[column] == data].copy()

def split_column(df, column):
    df[column] = df[column].str.split(',')
    df_exploded = df.explode(column)
    df_exploded[column] = df_exploded[column].str.strip()
    return df_exploded

def compare_assets(df1, df2, column1, column2):
    df1_assets = set(df1[column1].str.strip())
    df2_assets = set(df2[column2].str.strip())

    missing_from_df2 = df1_assets - df2_assets  # in df1, not in df2 list
    missing_from_df1 = df2_assets - df1_assets  # in df2 list, not in df1
    matched = df1_assets & df2_assets

    return missing_from_df2, missing_from_df1, matched

def compare_to_masters(syncro_df, monthly_path, yearly_path, covered_path):
    monthly_df = split_column(load_csv(monthly_path), 'Asset Name(s) in Syncro')
    yearly_df = split_column(load_csv(yearly_path), 'Asset Name(s) in Syncro')
    covered_df = split_column(load_csv(covered_path), 'Asset Name(s) in Syncro')

    syncro_assets = set(syncro_df['name'].str.strip())
    monthly_assets = set(monthly_df['Asset Name(s) in Syncro'].str.strip())
    yearly_assets = set(yearly_df['Asset Name(s) in Syncro'].str.strip())
    covered_assets = set(covered_df['Asset Name(s) in Syncro'].str.strip())
    combined_master_assets = monthly_assets | yearly_assets

    rows = []

    # Syncro assets: matched if found in ANY master list
    for asset in syncro_assets:
        in_monthly = asset in monthly_assets
        in_yearly = asset in yearly_assets
        in_covered = asset in covered_assets

        if in_monthly and in_yearly:
            master_label = 'Monthly & Yearly'
        elif in_monthly:
            master_label = 'Monthly'
        elif in_yearly:
            master_label = 'Yearly'
        elif in_covered:
            master_label = 'Covered'
        else:
            master_label = 'None'

        status = 'matched' if (in_monthly or in_yearly or in_covered) else 'missing_from_master'
        rows.append({'asset_name': asset, 'status': status, 'master': master_label})

    # Master assets not found in Syncro at all
    missing_from_syncro = combined_master_assets - syncro_assets
    for asset in missing_from_syncro:
        in_monthly = asset in monthly_assets
        in_yearly = asset in yearly_assets
        master_label = 'Monthly & Yearly' if (in_monthly and in_yearly) else ('Monthly' if in_monthly else 'Yearly')
        rows.append({'asset_name': asset, 'status': 'missing_from_syncro', 'master': master_label})

    return pd.DataFrame(rows)

def refactor_today_date(today_date, comparison_date):
    """
        Reformats today_date to match the date format used in comparison_date
        (a sample date string from the column you're comparing against, e.g. '08-25-2026').
        """
    # TODAY_STR is built elsewhere as date.today().strftime("%m_%d_%Y") - parse it back to a date
    if isinstance(today_date, str):
        today_date = datetime.strptime(today_date, "%m_%d_%Y").date()

    # Detect the separator used in the comparison date
    sep = '-' if '-' in comparison_date else '/'

    refactored_today_date = today_date.strftime(f"%m{sep}%d{sep}%Y")
    return refactored_today_date

def renewal_from_today(df, column, today_date, day_count, renewal_type):
    """
        Returns a DataFrame of rows whose renewal date falls within the next 7 days.
        """
    df = df.copy()

    # Grab a real date value from the column to detect its format (skips blanks/"Waiting")
    valid_dates = df[column].dropna()
    valid_dates = valid_dates[valid_dates.str.match(r'^\d{2}[-/]\d{2}[-/]\d{4}$', na=False)]
    if valid_dates.empty:
        return df.iloc[0:0]  # nothing usable to compare against

    sample_date = valid_dates.iloc[0]
    sep = '-' if '-' in sample_date else '/'
    date_format = f"%m{sep}%d{sep}%Y"

    refactored_today = refactor_today_date(today_date, sample_date)
    today_ts = pd.to_datetime(refactored_today, format=date_format)

    df['renewal_date'] = pd.to_datetime(df[column], format=date_format, errors='coerce')
    df['days_until_renewal'] = df['renewal_date'].apply(
        lambda d: calculate_days(today_ts, d).days if pd.notna(d) else None
    )

    renews_soon_df = df[
        df['days_until_renewal'].notna()
        & (df['days_until_renewal'] >= 0)
        & (df['days_until_renewal'] <= day_count)
        ].copy()

    renews_soon_df["Today's Date:"] = refactored_today
    renews_soon_df['Renewal Type'] = renewal_type
    renews_soon_df = renews_soon_df.drop(columns=['Unnamed: 4', 'Click button to sort by:'])

    return renews_soon_df

def normalize_for_comparison(df, sort_column):
    df = df.copy()
    if df.empty or sort_column not in df.columns:
        return df.astype(str)  # nothing to sort - just return as-is
    df = df.astype(str)
    df = df.sort_values(by=sort_column).reset_index(drop=True)
    return df

def main():
    syncro_df = load_csv(SYNCRO_ASSETS_FILE)
    yearly_df = load_csv(TECH_DOCTORS_MASTER_YEARLY)
    monthly_df = load_csv(TECH_DOCTORS_MASTER_MONTHLY)
    old_renew_df = load_csv_if_exists(OLD_RENEW_SOON)

    tech_doctors_df = strip_column_data(syncro_df, 'customer_business_name', 'Tech Doctor Renewal')

    mass_update_csv(syncro_df)

    need_fixed_td = compare_to_masters(tech_doctors_df, TECH_DOCTORS_MASTER_MONTHLY, TECH_DOCTORS_MASTER_YEARLY, TECH_DOCTORS_MASTER_COVERED)
    make_csv(need_fixed_td, 'Need_Fixed_TD')

    renews_soon_yearly_df = renewal_from_today(yearly_df, 'Renewal', TODAY_STR, 14, 'Yearly')
    renews_soon_monthly_df = renewal_from_today(monthly_df, 'Renewal', TODAY_STR, 14, 'Monthly')
    renews_soon_df = pd.concat([renews_soon_yearly_df, renews_soon_monthly_df], ignore_index=True)

    old_normalized = normalize_for_comparison(old_renew_df, 'Customer')
    new_normalized = normalize_for_comparison(renews_soon_df, 'Customer')

    make_csv(old_normalized, 'Old_Renew_Soon')

    if old_normalized.equals(new_normalized):
        print("No renewals coming")
    else:
        print("Renewals coming")
        make_csv(renews_soon_df, 'Renew_Soon')

        attachment_path = os.path.join(BASE_DIR, 'Data', 'Renew_Soon.csv')
        text_content = "Tech Doctor Report!\nBelow is the current information on Tech Doctor customers."
        html_content = """\
            <html>
              <body>
                <h2 style="color: #2e6cbb;">Tech Doctor Report!</h2>
                <p>A ticket has been created that has customers that will be needing to renew Tech Doctor's.</p>
              </body>
            </html>
            """

        send_email(
            receiver_emails=["support@testdomain.com .com"],
            subject="Automated Tech Doctor Report",
            text_content=text_content,
            html_content=html_content,
            attachment_path=attachment_path,
            sender_email="info@testdomain.com .com",
            provider=EMAIL_PROVIDER,
        )

    return 0

if __name__ == '__main__':
    main()

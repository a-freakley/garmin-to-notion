import os
from datetime import date
from dotenv import load_dotenv
from garminconnect import Garmin
from notion_client import Client


def get_average_respiration(respiration_data: list[dict]) -> float | None:
    """Compute the average respiration value from Garmin respiration data."""
    if not respiration_data:
        return None
    total = 0
    count = 0
    for entry in respiration_data:
        # Each entry may have keys like 'averageRespirationValue'
        value = entry.get("averageRespirationValue")
        if value is not None:
            total += value
            count += 1
    if count == 0:
        return None
    return total / count


def sync_health():
    """
    Log today's heart‑rate and respiration data into Notion.

    Environment variables needed:
      - GARMIN_EMAIL / GARMIN_PASSWORD: your Garmin Connect login
      - NOTION_TOKEN: your Notion integration token
      - NOTION_HEART_RATE_DB_ID: database ID for your heart‑rate table
      - NOTION_RESPIRATION_DB_ID: database ID for your respiration table
    """
    load_dotenv()

    # Read credentials and database IDs from environment
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    heart_db_id = os.getenv("NOTION_HEART_RATE_DB_ID")
    resp_db_id = os.getenv("NOTION_RESPIRATION_DB_ID")

    if not all([garmin_email, garmin_password, notion_token]):
        raise ValueError("Missing Garmin or Notion credentials in environment")

    # Log in to Garmin and Notion
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    notion = Client(auth=notion_token)

    today_str = date.today().isoformat()

    # --- Heart‑rate ---
    try:
        hr_data = garmin.get_heart_rates(today_str)
    except Exception as e:
        print(f"Could not fetch heart‑rate data: {e}")
        hr_data = None

    if hr_data and heart_db_id:
        # Resting heart rate is included under 'restingHeartRate'
        resting_hr = hr_data.get('restingHeartRate')
        # Create a page in the Heart Rate database
        notion.pages.create(
            parent={"database_id": heart_db_id},
            properties={
                "Date": {"date": {"start": today_str}},
                "Resting Heart Rate": {"number": resting_hr if resting_hr else 0},
            },
        )
        print(f"Uploaded heart‑rate data for {today_str}")

    # --- Respiration ---
    try:
        resp_data = garmin.get_respiration_data(today_str)
    except Exception as e:
        print(f"Could not fetch respiration data: {e}")
        resp_data = None

    if resp_data and resp_db_id:
        avg_resp = get_average_respiration(resp_data)
        if avg_resp is not None:
            notion.pages.create(
                parent={"database_id": resp_db_id},
                properties={
                    "Date": {"date": {"start": today_str}},
                    "Average Respiration": {"number": round(avg_resp, 2)},
                },
            )
            print(f"Uploaded respiration data for {today_str}")


if __name__ == "__main__":
    sync_health()

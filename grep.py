import requests
import json
import time
from pathlib import Path

BASE_URL = "https://indico.cern.ch"
API_TOKEN = ""
EVENTS_FILE = "events.json"
OUTPUT_DIR = Path("data")

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
}

def load_events(filepath):
    with open(filepath, "r") as f:
        return json.load(f)["events"]

def fetch_contributions(event_id):
    url = f"{BASE_URL}/export/event/{event_id}.json?detail=contributions"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["results"][0]["contributions"]

def parse_person(p):
    return {
        "full_name": p.get("fullName"),
        "affiliation": p.get("affiliation"),
        "email": p.get("email"),
    }

def parse_attachment(a):
    return {
        "title": a.get("title"),
        "filename": a.get("filename"),
        "download_url": a.get("download_url"),
        "content_type": a.get("content_type"),
        "is_protected": a.get("is_protected"),
        "size": a.get("size"),
    }

def parse_contribution(item, event_id):
    attachments = [
        parse_attachment(a)
        for folder in item.get("folders", [])
        for a in folder.get("attachments", [])
    ]

    return {
        "id": item.get("friendly_id"),
        "db_id": item.get("db_id"),
        "title": item.get("title"),
        "abstract": item.get("description"),
        "duration_minutes": item.get("duration"),
        "start_time": f"{item['startDate']['date']} {item['startDate']['time']} {item['startDate']['tz']}" if item.get("startDate") else None,
        "end_time": f"{item['endDate']['date']} {item['endDate']['time']} {item['endDate']['tz']}" if item.get("endDate") else None,
        "room": item.get("roomFullname"),
        "location": item.get("location"),
        "session": item.get("session"),
        "track": item.get("track"),
        "type": item.get("type"),
        "keywords": item.get("keywords", []),
        "speakers": [parse_person(p) for p in item.get("speakers", [])],
        "primary_authors": [parse_person(p) for p in item.get("primaryauthors", [])],
        "coauthors": [parse_person(p) for p in item.get("coauthors", [])],
        "references": item.get("references", []),
        "attachments": attachments,
        "url": f"{BASE_URL}/event/{event_id}/contributions/{item.get('db_id')}",
    }

def export_event(event):
    event_id = event["event_id"]
    year = event["year"]
    edition = event["edition"]

    print(f"\nFetching event {event_id} (Edition {edition}, {year})...")
    try:
        raw_contributions = fetch_contributions(event_id)
    except requests.exceptions.HTTPError as e:
        print(f"  ERROR fetching event {event_id}: {e}")
        return None

    contributions = [parse_contribution(c, event_id) for c in raw_contributions]
    print(f"  Found {len(contributions)} contributions.")

    result = {
        "event_id": event_id,
        "year": year,
        "edition": edition,
        "url": event["url"],
        "contributions": contributions,
    }

    # Save per-event file
    output_file = OUTPUT_DIR / f"event_{year}_edition{edition}_{event_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {output_file}")

    return result

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    events = load_events(EVENTS_FILE)
    all_events = []

    for event in events:
        result = export_event(event)
        if result:
            all_events.append(result)
        time.sleep(1)  # be polite to the server

    # Save combined file
    combined_file = OUTPUT_DIR / "all_events.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Exported {sum(len(e['contributions']) for e in all_events)} total contributions across {len(all_events)} events.")
    print(f"Combined output saved to {combined_file}")

if __name__ == "__main__":
    main()
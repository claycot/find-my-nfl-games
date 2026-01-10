from bs4 import BeautifulSoup, Tag
import cloudscraper
import re
import requests
from PIL import Image
from collections import Counter
from io import BytesIO
from pathlib import Path
import json

BASE_URL = "https://www.506sports.com/"
OUTPUT_DIR = Path("./output")


def main():
    # --- Load page ---
    # scraper = cloudscraper.create_scraper()
    # page_text = scraper.get("https://506sports.com/nfl.php?yr=2025&wk=18").text
    # For offline testing, use:
    with open("week18.html") as f: page_text = f.read()

    soup = BeautifulSoup(page_text, "html.parser")

    # --- National broadcasts ---
    national_games_raw = find_national_games(soup)
    national_games = parse_national_games(national_games_raw)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "national_broadcasts.json").write_text(json.dumps(national_games, indent=2))

    # --- Local games (maps + legends) ---
    broadcast_sections = parse_broadcast_sections(soup)
    for section in broadcast_sections:
        save_broadcast_section(section)

    print("Done!")


# -------------------
# National broadcasts
# -------------------

def find_national_games(soup: BeautifulSoup) -> list[str]:
    header_text = soup.find(string=lambda s: s and s.strip() == "NATIONAL BROADCASTS")
    anchor = header_text.find_parent("b")
    items = []
    collecting = False
    for sibling in anchor.next_siblings:
        if not isinstance(sibling, Tag):
            continue
        if sibling.name == "li":
            collecting = True
            items.append(sibling.get_text(strip=True))
        elif collecting:
            break
    return items


def looks_like_time(text: str, regex) -> bool:
    return bool(regex.search(text) or any(x in text for x in ["Night", "Afternoon", "Morning"]))


def split_day_and_time(header: str) -> tuple[str, str | None]:
    parts = header.split(maxsplit=1)
    day = parts[0]
    time = parts[1] if len(parts) > 1 else None
    return day, time


def split_time_and_rest(line: str, regex) -> tuple[str, str]:
    parts = line.split(":")
    time_parts = [parts[0]]
    for part in parts[1:]:
        candidate = ":".join(time_parts)
        if looks_like_time(candidate, regex):
            rest = ":".join(parts[len(time_parts):])
            return candidate.strip(), rest.strip()
        time_parts.append(part)
    raise ValueError(f"Could not determine time segment in line: {line}")


def parse_national_games(games_raw: list[str]) -> list[dict]:
    games = []
    TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
    for game_raw in games_raw:
        header, rest = split_time_and_rest(game_raw, TIME_RE)
        day, time = split_day_and_time(header)

        paren_parts = re.findall(r"\(([^)]+)\)", rest)
        matchup = rest.split("(")[0].strip()

        location = None
        broadcast = None
        announcers = None

        for p in paren_parts:
            if p.startswith("in "):
                location = p
            else:
                if ";" in p:
                    broadcast, announcers = map(str.strip, p.split(";", 1))
                else:
                    broadcast = p

        games.append({
            "day": day,
            "time": time,
            "matchup": matchup,
            "location": location,
            "broadcast": broadcast,
            "announcers": announcers,
        })

    return games


# -------------------
# Local games (maps + legends)
# -------------------

def download_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGBA")


def dominant_rgba(img: Image.Image) -> tuple[int, int, int, int]:
    pixels = list(img.get_flattened_data())
    return Counter(pixels).most_common(1)[0][0]


def parse_broadcast_sections(soup: BeautifulSoup) -> list[dict]:
    sections = []
    headers = soup.find_all(
        lambda t: isinstance(t, Tag)
        and t.name == "font"
        and t.get("size") == "5"
        and t.get_text(strip=True) != "NATIONAL BROADCASTS"
    )
    for header in headers:
        title = header.get_text(strip=True)
        node = header.find_parent("p")
        map_img_url = None
        games = []
        for sib in node.next_siblings:
            if not isinstance(sib, Tag):
                continue
            if sib.name == "div" and sib.get("id") == "map":
                img = sib.find("img")
                if img:
                    map_img_url = BASE_URL + img["src"]
            elif sib.name == "div" and sib.get("id") == "game":
                swatch = sib.find("div", id="square").img["src"]
                matchup = sib.find("div", id="matchup").get_text(strip=True)
                announcers = sib.find("div", id="anncrs").get_text(strip=True)
                games.append({
                    "swatch_url": BASE_URL + swatch,
                    "matchup": matchup,
                    "announcers": announcers,
                })
            elif sib.find("font", size="5"):
                break
        sections.append({
            "title": title,
            "map_image_url": map_img_url,
            "games": games,
        })
    return sections


def save_broadcast_section(section: dict):
    section_dir = OUTPUT_DIR / section["title"].replace(" ", "_")
    section_dir.mkdir(parents=True, exist_ok=True)
    network, time = section["title"].split(" ")

    # --- Save map PNG ---
    map_path = section_dir / "map.png"
    if section["map_image_url"]:
        img = download_image(section["map_image_url"])
        img.save(map_path)

    # --- Build legend ---
    legend = {}
    for game in section["games"]:
        swatch_img = download_image(game["swatch_url"])
        rgba = dominant_rgba(swatch_img)
        # Keep RGBA as string
        legend[str(rgba)] = {
            "day": "Sunday",
            "time": time,
            "matchup": game["matchup"],
            "location": None,
            "broadcast": network,
            "announcers": game["announcers"]
        }

    # --- Save legend JSON ---
    with open(section_dir / "legend.json", "w") as f:
        json.dump(legend, f, indent=2)



if __name__ == "__main__":
    main()
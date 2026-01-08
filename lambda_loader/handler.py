from bs4 import BeautifulSoup, Tag
from collections import Counter
from io import BytesIO
from PIL import Image
import cloudscraper
import re
import requests

BASE_URL = "https://www.506sports.com/"


def main() -> int:
    # Load HTML (use cloudscraper.get for live pages)
    # scraper = cloudscraper.create_scraper()

    # page = scraper.get("https://506sports.com/nfl.php?yr=2025&wk=18").text
    with open("week18.html") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    national_games = parse_national_games(soup)
    local_games = parse_local_games(soup)

    print(national_games)
    print(local_games)
    return 0


# ------------------ National Games ------------------ #

def parse_national_games(soup: BeautifulSoup) -> list[dict]:
    items = find_national_games(soup)
    parsed = []

    time_re = re.compile(r"\b\d{1,2}:\d{2}\b")

    for item in items:
        header, rest = split_time_and_rest(item, time_re)
        day, time = split_day_and_time(header)
        matchup, location, broadcast, announcers = parse_rest(rest)

        parsed.append({
            "day": day,
            "time": time,
            "matchup": matchup,
            "location": location,
            "broadcast": broadcast,
            "announcers": announcers
        })

    return parsed


def find_national_games(soup: BeautifulSoup) -> list[str]:
    header_text = soup.find(string=lambda s: s and s.strip() == "NATIONAL BROADCASTS")
    anchor = header_text.find_parent("b")
    items, collecting = [], False

    for sib in anchor.next_siblings:
        if not isinstance(sib, Tag):
            continue
        if sib.name == "li":
            collecting = True
            items.append(sib.get_text(strip=True))
        elif collecting:
            break

    return items


def split_time_and_rest(line: str, regex) -> tuple[str, str]:
    parts, time_parts = line.split(":"), []

    for part in parts:
        time_parts.append(part)
        candidate = ":".join(time_parts)
        if looks_like_time(candidate, regex):
            rest = ":".join(parts[len(time_parts):])
            return candidate.strip(), rest.strip()
    raise ValueError(f"Could not determine time in line: {line}")


def split_day_and_time(header: str) -> tuple[str, str | None]:
    parts = header.split(maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else None


def looks_like_time(text: str, regex) -> bool:
    return bool(regex.search(text) or any(x in text for x in ["Night", "Afternoon", "Morning"]))


def parse_rest(rest: str) -> tuple[str, str | None, str | None, str | None]:
    matchup = rest.split("(")[0].strip()
    paren_parts = re.findall(r"\(([^)]+)\)", rest)
    location = broadcast = announcers = None

    for p in paren_parts:
        if p.startswith("in "):
            location = p
        elif ";" in p:
            broadcast, announcers = map(str.strip, p.split(";", 1))
        else:
            broadcast = p

    return matchup, location, broadcast, announcers


# ------------------ Local / Broadcast Maps ------------------ #

def parse_local_games(soup: BeautifulSoup) -> list[dict]:
    sections = parse_broadcast_sections(soup)
    results = []

    for section in sections:
        results.append({
            "title": section["title"],
            "map_image": section["map_image"],
            "legend": build_section_legend(section)
        })

    return results


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
                img_tag = sib.find("img")
                if img_tag:
                    map_img_url = BASE_URL + img_tag["src"]

            elif sib.name == "div" and sib.get("id") == "game":
                swatch = sib.find("div", id="square").img["src"]
                matchup = sib.find("div", id="matchup").get_text(strip=True)
                announcers = sib.find("div", id="anncrs").get_text(strip=True)

                games.append({
                    "swatch_url": BASE_URL + swatch,
                    "matchup": matchup,
                    "announcers": announcers
                })

            elif sib.find("font", size="5"):
                break

        sections.append({
            "title": title,
            "map_image": map_img_url,
            "games": games
        })

    return sections


def build_section_legend(section: dict) -> dict:
    legend = {}
    for game in section["games"]:
        img = download_image(game["swatch_url"])
        rgba = dominant_rgba(img)
        legend[rgba] = {"matchup": game["matchup"], "announcers": game["announcers"]}
    return legend


def download_image(url: str) -> Image.Image:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGBA")


def dominant_rgba(img: Image.Image) -> tuple[int, int, int, int]:
    get_data = getattr(img, "get_flattened_data", img.getdata)
    pixels = list(get_data())
    return Counter(pixels).most_common(1)[0][0]


# ------------------ Run ------------------ #

if __name__ == "__main__":
    main()

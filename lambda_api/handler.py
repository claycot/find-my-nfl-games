from PIL import Image
from pathlib import Path
import json
from typing import Tuple
from typing import TypedDict, Optional

class GameInfo(TypedDict):
    day: str
    time: str
    matchup: str
    location: Optional[str]
    broadcast: str
    announcers: str

def main() -> list[GameInfo]:
    # Temp dir that mirrors s3
    map_dir_str = '../s3/2025/week_18'
    map_dir = Path(map_dir_str)

    # Keep the user's coordinates
    # game in Minnesota
    # x = 650
    # y = 150

    # game in MIN, but on the M
    # x = 684
    # y = 177

    # game in NYC, but on the Y
    # x = 1102
    # y = 303

    # game in PHL, but on the P
    x = 1065
    y = 327

    # add the national games
    games = []
    with open(Path(map_dir, "national_broadcasts.json")) as file:
        games += json.load(file)

    # add the local games
    for dir in map_dir.iterdir():
        # ignore the national broadcasts JSON
        if not dir.is_dir():
            continue
        
        # at this point there will be a map.png and legend.json
        img = Image.open(dir / "map.png")
        pixels = img.load()
        legend = None
        with open(dir / "legend.json") as file:
            raw_legend = json.load(file)
            # convert string keys to tuple
            legend = {tuple(map(int, k.strip("()").split(","))): v for k, v in raw_legend.items()}

        found_game = find_local_game((x, y), pixels, img.size, legend)
        if found_game:
            games.append(found_game)

    # sort and return games
    DAY_ORDER = {
        'Tuesday': 0, 
        'Wednesday': 1, 
        'Thursday': 2,
        'Friday': 3, 
        'Saturday': 4, 
        'Sunday': 5, 
        'Monday': 6, 
    }

    sorted_games = sorted(games, key=lambda game: DAY_ORDER.get(game["day"]))

    with open("games.json", "w", encoding="utf-8") as f:
        json.dump(sorted_games, f, indent=2)

    return(sorted_games)


def find_local_game(
        coordinates: Tuple[int, int],
        pixels: Image.PixelAccess,
        dimensions: Tuple[int, int],
        legend: dict[tuple[int, int, int, int], GameInfo]
) -> Optional[GameInfo]:
    cx, cy = coordinates

    # find the nearest clicked pixel that's in the legend
    pixel_RGBA = pixels[cx, cy]
    
    found_game = None
    # if the game is in the legend, we found it!
    if pixel_RGBA in legend:
        found_game = legend[pixel_RGBA]
    # otherwise, search with an expanding radius
    else:
        found_game = search_nearby_pixels(coordinates, pixels, dimensions, legend)

    # Print the result
    # print(f"Found a local game at {(cx, cy)}: {found_game}")
    return found_game


def search_nearby_pixels(
    coordinates: Tuple[int, int],
    pixels: Image.PixelAccess,
    dimensions: Tuple[int, int],
    legend: dict[tuple[int, int, int, int], GameInfo],
    search_radius_limit: int = 10,
) -> Optional[GameInfo]:
    cx, cy = coordinates
    width, height = dimensions

    for radius in range(1, search_radius_limit + 1):
        # Manhattan diamond: |dx| + |dy| = radius
        for dx in range(-radius, radius + 1):
            dy = radius - abs(dx)

            for sign in (-1, 1):
                x = cx + dx
                y = cy + sign * dy

                # Bounds check
                if not (0 <= x < width and 0 <= y < height):
                    continue

                pixel = pixels[x, y]

                if pixel in legend:
                    found_game = legend[pixel]
                    # print(f"found game {found_game} at radius {radius}")
                    return found_game

    print(f"did not find game after searching up to radius {search_radius_limit}")
    return None


if __name__ == "__main__":
    main()
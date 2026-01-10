from PIL import Image
from pathlib import Path
import json
from typing import Tuple

def main():
    # Keep the dir for the current map (will become a loop)
    map_dir = '../s3/2025/week_18/cbs_early/'

    # build the legend
    legend = build_legend(map_dir)
    print(legend)

    # Open the image file
    img = Image.open(map_dir + "map.png")

    # Load the pixels
    pixels = img.load()
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

    pixel_RGBA = pixels[x, y]
    print(pixel_RGBA)

    found_game = None
    # if the game is in the legend, we found it!
    if pixel_RGBA in legend:
        found_game = legend[pixel_RGBA]
    # otherwise, search with an expanding radius
    else:
        found_game = search_nearby_pixels(legend, pixels, (x, y))

    # Print the result
    print(f"The game available at at {(x, y)} is: {found_game}")

def build_legend(dir: str) -> dict[str, str]:
    legend = {}

    # Loop over each of the legend entries to get valid colors
    for legend_img_path in Path(dir + "/legend").iterdir():
        if legend_img_path.is_file() and legend_img_path.name.endswith(".png"):
            idx = int(legend_img_path.name.split(".")[0]) - 1

            pixel_count = {}
            with Image.open(legend_img_path) as img:
                # Load the pixel data
                pixels = img.load()
                width, height = img.size

                for r in range(height):
                    for c in range(width):
                        p = pixels[r, c]
                        if p not in pixel_count:
                            pixel_count[p] = 0
                        pixel_count[p] += 1

            most_common_pixel_RGBA = max(pixel_count, key=pixel_count.get)
            legend[most_common_pixel_RGBA] = idx
    
    with open(dir + "legend/legend.json") as legend_JSON:
        data = json.load(legend_JSON)
        for pixel in legend:
            idx = legend[pixel]
            legend[pixel] = data['entries'][idx]

    return legend

def search_nearby_pixels(legend: dict[str, str], pixels: list[list[any]], coordinates: Tuple[int, int]) -> str:
    # set a radius (pixel) limit on how far we will search before giving up
    # note that the worst case becomes (8 * radius) because of the search pattern
    SEARCH_RADIUS_LIMIT = 10

    # search pattern is cardinal directions first, then intercardinal (as they're technically further)
    SEARCH_PATTERN = [
        (-1, 0), (0, 1), (1, 0), (0, -1),
        (-1, 1), (1, 1), (1, -1), (-1, -1),
    ]

    # search in an expanding circle for a match
    for radius in range(SEARCH_RADIUS_LIMIT):
        for dir in SEARCH_PATTERN:
            search_x = coordinates[0] + (radius * dir[0])
            search_y = coordinates[1] + (radius * dir[1])

            pixel_RGBA = pixels[search_x, search_y]
            if (pixel_RGBA in legend):
                found_game = legend[pixel_RGBA]
                print(f"found game {found_game} at radius {radius}")
                return found_game
    
    print(f"did not find game after searching at radius {radius}")
    return None

if __name__ == "__main__":
    main()
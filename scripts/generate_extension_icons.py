"""One-off script: generates the extension's toolbar/store icons (16/48/128px).

Draws a simple shield-with-checkmark placeholder in the extension's blue/red
palette. Run once; regenerate only if the visual design changes.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "extension" / "icons"
SIZES = (16, 48, 128)

BLUE = (37, 99, 235, 255)
BLUE_DARK = (29, 78, 216, 255)
WHITE = (255, 255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx = s / 2
    top = s * 0.06
    bottom = s * 0.94
    half_w = s * 0.40

    shield = [
        (cx, top),
        (cx + half_w, top + s * 0.14),
        (cx + half_w, s * 0.55),
        (cx, bottom),
        (cx - half_w, s * 0.55),
        (cx - half_w, top + s * 0.14),
    ]
    d.polygon(shield, fill=BLUE_DARK)

    inset = s * 0.07
    shield_in = [
        (cx, top + inset),
        (cx + half_w - inset, top + s * 0.14 + inset * 0.5),
        (cx + half_w - inset, s * 0.53),
        (cx, bottom - inset),
        (cx - half_w + inset, s * 0.53),
        (cx - half_w + inset, top + s * 0.14 + inset * 0.5),
    ]
    d.polygon(shield_in, fill=BLUE)

    check = [
        (cx - s * 0.20, s * 0.48),
        (cx - s * 0.06, s * 0.62),
        (cx + s * 0.24, s * 0.30),
        (cx + s * 0.17, s * 0.23),
        (cx - s * 0.06, s * 0.48),
        (cx - s * 0.13, s * 0.41),
    ]
    d.polygon(check, fill=WHITE)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        icon = draw_icon(size)
        path = OUT_DIR / f"icon{size}.png"
        icon.save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()

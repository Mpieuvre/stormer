"""Logo Stormer — C neon + barre foncee, rendu vectoriel propre."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent / "assets"
SOURCE = ROOT / "logo_source.png"

# Couleurs exactes mesurees sur logo_source.png
NEON = (2, 156, 255, 255)
NEON_HI = (72, 188, 255, 255)
DARK = (30, 32, 37, 255)
DARK_EDGE = (18, 20, 26, 255)

# Grille 24x24 calibree pixel par pixel sur logo_source (crop x9-20, y10-25)
GRID = 24
M = {
    "x0": 2.0,
    "y0": 2.0,
    "x1": 21.5,
    "y1": 21.5,
    "t": 5.0,
    "r": 3.5,
    "bar_x0": 16.0,
    "gap": 0.8,
}


def _px(v: float, size: int) -> int:
    return int(round(v * size / GRID))


def _ring_mask(size: int) -> Image.Image:
    """Masque de l'anneau (carre arrondi exterieur - trou interieur)."""
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = M["x0"], M["y0"], M["x1"], M["y1"]
    t, r, bar_x0 = M["t"], M["r"], M["bar_x0"]

    d.rounded_rectangle(
        [_px(x0, size), _px(y0, size), _px(x1, size), _px(y1, size)],
        radius=_px(r, size),
        fill=255,
    )

    hole = Image.new("L", (size, size), 0)
    hd = ImageDraw.Draw(hole)
    hx0 = x0 + t - 0.2
    hy0 = y0 + t - 0.2
    hx1 = bar_x0 - M["gap"] - 0.5
    hy1 = y1 - t + 0.2
    hr = max(1.0, r - 1.2)
    hd.rounded_rectangle(
        [_px(hx0, size), _px(hy0, size), _px(hx1, size), _px(hy1, size)],
        radius=_px(hr, size),
        fill=255,
    )
    return ImageChops.subtract(m, hole)


def _draw_logo(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ring = _ring_mask(size)
    bar_x = _px(M["bar_x0"], size)

    neon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rn = ring.load()
    nn = neon.load()
    nd = dark.load()

    for y in range(size):
        for x in range(size):
            if not rn[x, y]:
                continue
            if x >= bar_x:
                nd[x, y] = DARK
            else:
                nn[x, y] = NEON

    img = Image.alpha_composite(img, neon)
    img = Image.alpha_composite(img, dark)

    # Liseret neon (haut + gauche) — comme l'original
    draw = ImageDraw.Draw(img)
    x0, y0 = M["x0"], M["y0"]
    neon_x1 = M["bar_x0"] - M["gap"]
    lw = max(1, _px(0.45, size))
    draw.line(
        [_px(x0 + M["r"], size), _px(y0 + 0.35, size),
         _px(neon_x1, size), _px(y0 + 0.35, size)],
        fill=NEON_HI,
        width=lw,
    )
    draw.line(
        [_px(x0 + 0.35, size), _px(y0 + M["r"], size),
         _px(x0 + 0.35, size), _px(M["y1"] - M["r"], size)],
        fill=NEON_HI,
        width=lw,
    )

    # Ombre interne discrete sur la barre
    draw.line(
        [_px(M["bar_x0"] + 0.6, size), _px(M["y0"] + M["r"], size),
         _px(M["bar_x0"] + 0.6, size), _px(M["y1"] - M["r"], size)],
        fill=DARK_EDGE,
        width=max(1, lw),
    )

    return img


def _extract_from_source() -> Image.Image | None:
    """Extrait l'icone depuis logo_source.png si disponible."""
    if not SOURCE.is_file():
        return None
    src = Image.open(SOURCE).convert("RGBA")
    # Crop icone seule (sans le S a droite)
    icon = src.crop((9, 10, 21, 26))
    out = Image.new("RGBA", (icon.width, icon.height), (0, 0, 0, 0))
    px = icon.load()
    op = out.load()
    for y in range(icon.height):
        for x in range(icon.width):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            if r < 20 and g > 130 and b > 180:
                op[x, y] = NEON
            elif 20 < r < 50 and 20 < g < 50 and 25 < b < 55:
                op[x, y] = DARK
            elif r < 25 and g < 25 and b < 25:
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (0, 0, 0, 0)
    return out


def _render(size: int) -> Image.Image:
    """Rendu vectoriel 8x puis downscale LANCZOS pour bords propres."""
    big = _draw_logo(size * 8)
    return big.resize((size, size), Image.Resampling.LANCZOS)


def make_logo_png(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _render(size).save(path, "PNG")


def make_banner_png(path: Path, w: int = 164, h: int = 314) -> None:
    img = Image.new("RGBA", (w, h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        c = (int(15 + 20 * t), int(23 + 24 * t), int(42 + 32 * t), 255)
        draw.line([(0, y), (w, y)], fill=c)
    icon = _render(96)
    img.paste(icon, ((w - 96) // 2, 42), icon)
    draw.text((w // 2, 168), "STORMER", fill=(226, 232, 240, 255), anchor="mm")
    draw.text((w // 2, 194), "v1.0", fill=(100, 116, 139, 255), anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def make_ico(path: Path) -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    images = [_render(s) for s in sizes]
    images[0].save(path, format="ICO", sizes=[(s, s) for s in sizes])


if __name__ == "__main__":
    make_logo_png(ROOT / "stormer_logo.png", 512)
    make_logo_png(ROOT / "stormer_logo_sm.png", 128)
    make_banner_png(ROOT / "installer_banner.png")
    make_ico(ROOT / "stormer.ico")
    print("Logo OK ->", ROOT)

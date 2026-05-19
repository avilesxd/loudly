"""Genera assets/loudly.ico con el logo de Loudly."""

from pathlib import Path

from PIL import Image, ImageDraw


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = size * 0.04
    d.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(40, 16, 90, 255),
    )
    inner = size * 0.08
    d.ellipse(
        [inner, inner, size - inner, size - inner],
        fill=(60, 24, 130, 255),
    )

    n_bars = 7
    bar_w = size * 0.055
    gap = size * 0.03
    heights = [0.30, 0.52, 0.70, 0.85, 0.70, 0.52, 0.30]
    total_w = n_bars * bar_w + (n_bars - 1) * gap
    x_start = (size - total_w) / 2
    cy = size / 2

    for i, h in enumerate(heights):
        x0 = x_start + i * (bar_w + gap)
        x1 = x0 + bar_w
        half_h = (size * h) / 2
        y0 = cy - half_h
        y1 = cy + half_h
        r = bar_w / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(200, 160, 255, 255))

    border_w = max(1, int(size * 0.025))
    half = border_w / 2
    d.ellipse(
        [half, half, size - half, size - half],
        outline=(150, 100, 230, 180),
        width=border_w,
    )

    return img


sizes = [256, 128, 64, 48, 32, 16]
frames = [draw_icon(s) for s in sizes]

out = Path(__file__).parent / "loudly.ico"
frames[0].save(
    out,
    format="ICO",
    append_images=frames[1:],
)
print(f"Icono generado: {out} ({out.stat().st_size} bytes)")

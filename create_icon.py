"""Script to regenerate icon.ico and web/favicon.ico from Lyriq Brand Assets."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "Lyriq_Brand_Assets"
LOGO_SYMBOL = ASSETS_DIR / "02_Logos" / "logo-symbol.png"
ICON_ICO = ROOT / "icon.ico"
FAVICON_ICO = ROOT / "web" / "favicon.ico"


def generate_icons():
    if not LOGO_SYMBOL.is_file():
        raise FileNotFoundError(f"Missing brand symbol at {LOGO_SYMBOL}")

    sym = Image.open(LOGO_SYMBOL)
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    sym.save(ICON_ICO, format="ICO", sizes=ico_sizes)
    sym.save(FAVICON_ICO, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
    print(f"Icons generated successfully at {ICON_ICO} and {FAVICON_ICO}")


if __name__ == "__main__":
    generate_icons()

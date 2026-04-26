"""Korean font setup for matplotlib (macOS AppleGothic)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def setup_korean_font():
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                font_manager.fontManager.addfont(fp)
                fname = font_manager.FontProperties(fname=fp).get_name()
                plt.rcParams["font.family"] = fname
                plt.rcParams["axes.unicode_minus"] = False
                return fname
            except Exception:
                continue
    return None

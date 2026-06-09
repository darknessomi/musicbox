r"""
__   ___________________________________________
| \  ||______   |   |______|_____||______|______
|  \_||______   |   |______|     |______||______

________     __________________________  _____ _     _
|  |  ||     ||______  |  |      |_____]|     | \___/
|  |  ||_____|______|__|__|_____ |_____]|_____|_/   \_


+ ------------------------------------------ +
|   NetEase-MusicBox               320kbps   |
+ ------------------------------------------ +
|                                            |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|                                            |
|   A sexy cli musicbox based on Python      |
|   Music resource from music.163.com        |
|                                            |
|   Built with love to music by omi          |
|                                            |
+ ------------------------------------------ +

"""

from importlib.metadata import distributions

from .const import Constant
from .utils import create_dir, create_file


def _parse_version(version: str) -> tuple[int, ...]:
    parts = []
    for part in version.split("."):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


_versions = [_parse_version(d.version) for d in distributions(name="NetEase-MusicBox")]
__version__ = ".".join(map(str, max(_versions))) if _versions else "0.5.2"


def create_config():
    create_dir(Constant.conf_dir)
    create_dir(Constant.download_dir)
    create_file(Constant.storage_path)
    create_file(Constant.log_path, default="")
    create_file(Constant.cookie_path, default="# Netscape HTTP Cookie File\n")


create_config()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probolism Seestar simple goto browser v1_4 by piotrs

A small Windows-friendly Tkinter application that reads a Probolism CSV file and
sends simple GoTo commands to a Seestar telescope through ASCOM Alpaca over Wi-Fi.

Required package:
    python -m pip install requests

Notes:
    - This program sends simple telescope GoTo commands only.
    - It does not perform plate solving, centering, focusing, stacking, or imaging.
    - The Seestar must expose an ASCOM Alpaca telescope device on the same network.
    - To build a Windows EXE without a terminal window, use PyInstaller with --noconsole.
"""

from __future__ import annotations

import csv
import json
import queue
import re
import socket
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# -----------------------------------------------------------------------------
# Dependency check
# -----------------------------------------------------------------------------

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:  # pragma: no cover
    print("Tkinter is not available in this Python installation.", file=sys.stderr)
    print(exc, file=sys.stderr)
    raise SystemExit(1)

try:
    import requests
except Exception as exc:  # pragma: no cover
    root = tk.Tk()
    root.withdraw()
    cmd = f'"{sys.executable}" -m pip install requests'
    messagebox.showerror(
        "Missing Python package",
        "The required Python package 'requests' is missing.\n\n"
        "Install it with this command in PowerShell / Terminal:\n\n"
        f"{cmd}\n\n"
        f"Technical details:\n{exc}",
    )
    root.destroy()
    raise SystemExit(1)


APP_TITLE = "Probolism Seestar simple goto browser v1_4 by piotrs"
CLIENT_ID = 8123
ALPACA_DISCOVERY_PORT = 32227
ALPACA_DISCOVERY_MESSAGE = b"alpacadiscovery1"
DEFAULT_DISCOVERY_TIMEOUT_SEC = 5.0
DEFAULT_GOTO_TIMEOUT_SEC = 180.0

REQUIRED_COLUMNS = [
    "center_RA",
    "center_DEC",
    "center_RA_current",
    "center_DEC_current",
    "g_star",
    "g_gal",
    "galaxies",
    "P_raw",
    "P_norm",
    "klasa",
]


# Built-in Messier catalogue coordinates, J2000.0.
MESSIER_OBJECTS = [
    {"id": "M1", "name": "Crab Nebula", "ra": "05h34m31.9s", "dec": "+22d00m52s"},
    {"id": "M2", "name": "Globular Cluster in Aquarius", "ra": "21h33m27.0s", "dec": "-00d49m24s"},
    {"id": "M3", "name": "Globular Cluster in Canes Venatici", "ra": "13h42m11.6s", "dec": "+28d22m38s"},
    {"id": "M4", "name": "Globular Cluster in Scorpius", "ra": "16h23m35.2s", "dec": "-26d31m33s"},
    {"id": "M5", "name": "Globular Cluster in Serpens", "ra": "15h18m33.2s", "dec": "+02d04m51s"},
    {"id": "M6", "name": "Butterfly Cluster", "ra": "17h40m20s", "dec": "-32d15m12s"},
    {"id": "M7", "name": "Ptolemy Cluster", "ra": "17h53m51s", "dec": "-34d47m34s"},
    {"id": "M8", "name": "Lagoon Nebula", "ra": "18h03m37s", "dec": "-24d23m12s"},
    {"id": "M9", "name": "Globular Cluster in Ophiuchus", "ra": "17h19m11.8s", "dec": "-18d30m59s"},
    {"id": "M10", "name": "Globular Cluster in Ophiuchus", "ra": "16h57m08.9s", "dec": "-04d05m58s"},
    {"id": "M11", "name": "Wild Duck Cluster", "ra": "18h51m05s", "dec": "-06d16m12s"},
    {"id": "M12", "name": "Globular Cluster in Ophiuchus", "ra": "16h47m14.5s", "dec": "-01d56m52s"},
    {"id": "M13", "name": "Hercules Globular Cluster", "ra": "16h41m41.2s", "dec": "+36d27m36s"},
    {"id": "M14", "name": "Globular Cluster in Ophiuchus", "ra": "17h37m36.1s", "dec": "-03d14m45s"},
    {"id": "M15", "name": "Great Pegasus Cluster", "ra": "21h29m58.3s", "dec": "+12d10m01s"},
    {"id": "M16", "name": "Eagle Nebula", "ra": "18h18m48s", "dec": "-13d49m00s"},
    {"id": "M17", "name": "Omega Nebula", "ra": "18h20m47s", "dec": "-16d10m18s"},
    {"id": "M18", "name": "Open Cluster in Sagittarius", "ra": "18h19m58s", "dec": "-17d06m07s"},
    {"id": "M19", "name": "Globular Cluster in Ophiuchus", "ra": "17h02m37.8s", "dec": "-26d16m05s"},
    {"id": "M20", "name": "Trifid Nebula", "ra": "18h02m23s", "dec": "-23d01m48s"},
    {"id": "M21", "name": "Open Cluster in Sagittarius", "ra": "18h04m13s", "dec": "-22d29m24s"},
    {"id": "M22", "name": "Sagittarius Cluster", "ra": "18h36m24.2s", "dec": "-23d54m12s"},
    {"id": "M23", "name": "Open Cluster in Sagittarius", "ra": "17h56m56s", "dec": "-19d00m00s"},
    {"id": "M24", "name": "Sagittarius Star Cloud", "ra": "18h18m24s", "dec": "-18d24m00s"},
    {"id": "M25", "name": "Open Cluster in Sagittarius", "ra": "18h31m47s", "dec": "-19d06m54s"},
    {"id": "M26", "name": "Open Cluster in Scutum", "ra": "18h45m18s", "dec": "-09d23m00s"},
    {"id": "M27", "name": "Dumbbell Nebula", "ra": "19h59m36.3s", "dec": "+22d43m16s"},
    {"id": "M28", "name": "Globular Cluster in Sagittarius", "ra": "18h24m32.9s", "dec": "-24d52m11s"},
    {"id": "M29", "name": "Open Cluster in Cygnus", "ra": "20h23m56s", "dec": "+38d31m24s"},
    {"id": "M30", "name": "Globular Cluster in Capricornus", "ra": "21h40m22.1s", "dec": "-23d10m47s"},
    {"id": "M31", "name": "Andromeda Galaxy", "ra": "00h42m44.3s", "dec": "+41d16m09s"},
    {"id": "M32", "name": "Dwarf Elliptical Galaxy in Andromeda", "ra": "00h42m41.8s", "dec": "+40d51m55s"},
    {"id": "M33", "name": "Triangulum Galaxy", "ra": "01h33m50.9s", "dec": "+30d39m37s"},
    {"id": "M34", "name": "Open Cluster in Perseus", "ra": "02h42m05s", "dec": "+42d45m42s"},
    {"id": "M35", "name": "Open Cluster in Gemini", "ra": "06h08m54s", "dec": "+24d20m00s"},
    {"id": "M36", "name": "Open Cluster in Auriga", "ra": "05h36m18s", "dec": "+34d08m24s"},
    {"id": "M37", "name": "Open Cluster in Auriga", "ra": "05h52m18s", "dec": "+32d33m12s"},
    {"id": "M38", "name": "Open Cluster in Auriga", "ra": "05h28m42s", "dec": "+35d51m18s"},
    {"id": "M39", "name": "Open Cluster in Cygnus", "ra": "21h31m48s", "dec": "+48d26m00s"},
    {"id": "M40", "name": "Winnecke 4", "ra": "12h22m16s", "dec": "+58d05m04s"},
    {"id": "M41", "name": "Open Cluster in Canis Major", "ra": "06h46m00s", "dec": "-20d44m00s"},
    {"id": "M42", "name": "Orion Nebula", "ra": "05h35m17.3s", "dec": "-05d23m28s"},
    {"id": "M43", "name": "De Mairan's Nebula", "ra": "05h35m31.3s", "dec": "-05d16m12s"},
    {"id": "M44", "name": "Beehive Cluster", "ra": "08h40m24s", "dec": "+19d40m00s"},
    {"id": "M45", "name": "Pleiades", "ra": "03h47m00s", "dec": "+24d07m00s"},
    {"id": "M46", "name": "Open Cluster in Puppis", "ra": "07h41m46s", "dec": "-14d48m36s"},
    {"id": "M47", "name": "Open Cluster in Puppis", "ra": "07h36m36s", "dec": "-14d29m00s"},
    {"id": "M48", "name": "Open Cluster in Hydra", "ra": "08h13m43s", "dec": "-05d45m00s"},
    {"id": "M49", "name": "Elliptical Galaxy in Virgo", "ra": "12h29m46.7s", "dec": "+08d00m02s"},
    {"id": "M50", "name": "Open Cluster in Monoceros", "ra": "07h02m47s", "dec": "-08d20m00s"},
    {"id": "M51", "name": "Whirlpool Galaxy", "ra": "13h29m52.7s", "dec": "+47d11m43s"},
    {"id": "M52", "name": "Open Cluster in Cassiopeia", "ra": "23h24m48s", "dec": "+61d35m36s"},
    {"id": "M53", "name": "Globular Cluster in Coma Berenices", "ra": "13h12m55.3s", "dec": "+18d10m09s"},
    {"id": "M54", "name": "Globular Cluster in Sagittarius", "ra": "18h55m03.3s", "dec": "-30d28m47s"},
    {"id": "M55", "name": "Summer Rose Star", "ra": "19h39m59.7s", "dec": "-30d57m44s"},
    {"id": "M56", "name": "Globular Cluster in Lyra", "ra": "19h16m35.5s", "dec": "+30d11m04s"},
    {"id": "M57", "name": "Ring Nebula", "ra": "18h53m35.1s", "dec": "+33d01m45s"},
    {"id": "M58", "name": "Barred Spiral Galaxy in Virgo", "ra": "12h37m43.5s", "dec": "+11d49m05s"},
    {"id": "M59", "name": "Elliptical Galaxy in Virgo", "ra": "12h42m02.3s", "dec": "+11d38m49s"},
    {"id": "M60", "name": "Elliptical Galaxy in Virgo", "ra": "12h43m40.0s", "dec": "+11d33m09s"},
    {"id": "M61", "name": "Spiral Galaxy in Virgo", "ra": "12h21m54.9s", "dec": "+04d28m25s"},
    {"id": "M62", "name": "Globular Cluster in Ophiuchus", "ra": "17h01m12.8s", "dec": "-30d06m49s"},
    {"id": "M63", "name": "Sunflower Galaxy", "ra": "13h15m49.3s", "dec": "+42d01m45s"},
    {"id": "M64", "name": "Black Eye Galaxy", "ra": "12h56m43.7s", "dec": "+21d40m58s"},
    {"id": "M65", "name": "Leo Triplet Galaxy", "ra": "11h18m55.9s", "dec": "+13d05m32s"},
    {"id": "M66", "name": "Leo Triplet Galaxy", "ra": "11h20m15.0s", "dec": "+12d59m30s"},
    {"id": "M67", "name": "King Cobra Cluster", "ra": "08h51m18s", "dec": "+11d48m00s"},
    {"id": "M68", "name": "Globular Cluster in Hydra", "ra": "12h39m28.0s", "dec": "-26d44m34s"},
    {"id": "M69", "name": "Globular Cluster in Sagittarius", "ra": "18h31m23.1s", "dec": "-32d20m53s"},
    {"id": "M70", "name": "Globular Cluster in Sagittarius", "ra": "18h43m12.8s", "dec": "-32d17m31s"},
    {"id": "M71", "name": "Globular Cluster in Sagitta", "ra": "19h53m46.5s", "dec": "+18d46m42s"},
    {"id": "M72", "name": "Globular Cluster in Aquarius", "ra": "20h53m27.9s", "dec": "-12d32m14s"},
    {"id": "M73", "name": "Asterism in Aquarius", "ra": "20h58m56s", "dec": "-12d38m07s"},
    {"id": "M74", "name": "Phantom Galaxy", "ra": "01h36m41.7s", "dec": "+15d47m01s"},
    {"id": "M75", "name": "Globular Cluster in Sagittarius", "ra": "20h06m04.8s", "dec": "-21d55m17s"},
    {"id": "M76", "name": "Little Dumbbell Nebula", "ra": "01h42m19.7s", "dec": "+51d34m31s"},
    {"id": "M77", "name": "Cetus A", "ra": "02h42m40.8s", "dec": "-00d00m48s"},
    {"id": "M78", "name": "Reflection Nebula in Orion", "ra": "05h46m45s", "dec": "+00d03m00s"},
    {"id": "M79", "name": "Globular Cluster in Lepus", "ra": "05h24m10.6s", "dec": "-24d31m27s"},
    {"id": "M80", "name": "Globular Cluster in Scorpius", "ra": "16h17m02.4s", "dec": "-22d58m33s"},
    {"id": "M81", "name": "Bode's Galaxy", "ra": "09h55m33.2s", "dec": "+69d03m55s"},
    {"id": "M82", "name": "Cigar Galaxy", "ra": "09h55m52.7s", "dec": "+69d40m47s"},
    {"id": "M83", "name": "Southern Pinwheel Galaxy", "ra": "13h37m00.9s", "dec": "-29d51m57s"},
    {"id": "M84", "name": "Elliptical Galaxy in Virgo", "ra": "12h25m03.7s", "dec": "+12d53m13s"},
    {"id": "M85", "name": "Lenticular Galaxy in Coma Berenices", "ra": "12h25m24.1s", "dec": "+18d11m27s"},
    {"id": "M86", "name": "Lenticular Galaxy in Virgo", "ra": "12h26m12.2s", "dec": "+12d56m46s"},
    {"id": "M87", "name": "Virgo A", "ra": "12h30m49.4s", "dec": "+12d23m28s"},
    {"id": "M88", "name": "Spiral Galaxy in Coma Berenices", "ra": "12h31m59.2s", "dec": "+14d25m14s"},
    {"id": "M89", "name": "Elliptical Galaxy in Virgo", "ra": "12h35m39.8s", "dec": "+12d33m23s"},
    {"id": "M90", "name": "Spiral Galaxy in Virgo", "ra": "12h36m49.8s", "dec": "+13d09m46s"},
    {"id": "M91", "name": "Barred Spiral Galaxy in Coma Berenices", "ra": "12h35m26.4s", "dec": "+14d29m46s"},
    {"id": "M92", "name": "Globular Cluster in Hercules", "ra": "17h17m07.4s", "dec": "+43d08m11s"},
    {"id": "M93", "name": "Open Cluster in Puppis", "ra": "07h44m29s", "dec": "-23d51m12s"},
    {"id": "M94", "name": "Croc's Eye Galaxy", "ra": "12h50m53.1s", "dec": "+41d07m14s"},
    {"id": "M95", "name": "Barred Spiral Galaxy in Leo", "ra": "10h43m57.7s", "dec": "+11d42m14s"},
    {"id": "M96", "name": "Spiral Galaxy in Leo", "ra": "10h46m45.7s", "dec": "+11d49m12s"},
    {"id": "M97", "name": "Owl Nebula", "ra": "11h14m47.7s", "dec": "+55d01m09s"},
    {"id": "M98", "name": "Spiral Galaxy in Coma Berenices", "ra": "12h13m48.3s", "dec": "+14d54m01s"},
    {"id": "M99", "name": "Pinwheel Galaxy", "ra": "12h18m49.6s", "dec": "+14d25m00s"},
    {"id": "M100", "name": "Grand Design Spiral Galaxy", "ra": "12h22m54.9s", "dec": "+15d49m21s"},
    {"id": "M101", "name": "Pinwheel Galaxy", "ra": "14h03m12.6s", "dec": "+54d20m57s"},
    {"id": "M102", "name": "Spindle Galaxy", "ra": "15h06m29.5s", "dec": "+55d45m48s"},
    {"id": "M103", "name": "Open Cluster in Cassiopeia", "ra": "01h33m23s", "dec": "+60d39m00s"},
    {"id": "M104", "name": "Sombrero Galaxy", "ra": "12h39m59.4s", "dec": "-11d37m23s"},
    {"id": "M105", "name": "Elliptical Galaxy in Leo", "ra": "10h47m49.6s", "dec": "+12d34m54s"},
    {"id": "M106", "name": "Spiral Galaxy in Canes Venatici", "ra": "12h18m57.5s", "dec": "+47d18m14s"},
    {"id": "M107", "name": "Globular Cluster in Ophiuchus", "ra": "16h32m31.9s", "dec": "-13d03m13s"},
    {"id": "M108", "name": "Surfboard Galaxy", "ra": "11h11m31.0s", "dec": "+55d40m27s"},
    {"id": "M109", "name": "Barred Spiral Galaxy in Ursa Major", "ra": "11h57m36.0s", "dec": "+53d22m28s"},
    {"id": "M110", "name": "Dwarf Elliptical Galaxy in Andromeda", "ra": "00h40m22.1s", "dec": "+41d41m07s"},
]


@dataclass
class MessierObject:
    number: int
    label: str
    ra_hours: float
    ra_degrees: float
    dec_degrees: float
    ra_text: str
    dec_text: str
    object_type: str = ""
    common_name: str = ""


def _parse_messier_catalog() -> List[MessierObject]:
    objects: List[MessierObject] = []
    ra_pattern = re.compile(r"^\s*(\d+(?:\.\d+)?)h\s*(\d+(?:\.\d+)?)m(?:(\d+(?:\.\d+)?)s)?\s*$", re.IGNORECASE)
    dec_pattern = re.compile(r"^\s*([+-]?)(\d+(?:\.\d+)?)d\s*(\d+(?:\.\d+)?)m(?:(\d+(?:\.\d+)?)s)?\s*$", re.IGNORECASE)
    for item in MESSIER_OBJECTS:
        object_id = str(item["id"]).strip()
        number = int(object_id.lstrip("Mm"))
        ra_text = str(item["ra"]).strip()
        dec_text = str(item["dec"]).strip()
        ra_match = ra_pattern.match(ra_text)
        dec_match = dec_pattern.match(dec_text)
        if not ra_match or not dec_match:
            continue
        ra_hours = (
            float(ra_match.group(1))
            + float(ra_match.group(2)) / 60.0
            + float(ra_match.group(3) or 0.0) / 3600.0
        ) % 24.0
        sign = -1.0 if dec_match.group(1) == "-" else 1.0
        dec_degrees = sign * (
            float(dec_match.group(2))
            + float(dec_match.group(3)) / 60.0
            + float(dec_match.group(4) or 0.0) / 3600.0
        )
        common_name = str(item.get("name", "")).strip()
        label = f"{object_id} - {common_name}" if common_name else object_id
        objects.append(
            MessierObject(
                number=number,
                label=label,
                ra_hours=ra_hours,
                ra_degrees=ra_hours * 15.0,
                dec_degrees=dec_degrees,
                ra_text=ra_text,
                dec_text=dec_text,
                object_type="",
                common_name=common_name,
            )
        )
    return objects

MESSIER_CATALOG = _parse_messier_catalog()


@dataclass
class Target:
    row_number: int
    galaxies: str
    ra_text: str
    dec_text: str
    ra_hours: float
    ra_degrees: float
    dec_degrees: float
    g_star: str = ""
    g_gal: str = ""
    p_raw: str = ""
    p_norm: str = ""
    klasa: str = ""


@dataclass
class AlpacaDeviceInfo:
    host: str
    port: int
    device_number: int
    device_name: str
    device_type: str = "telescope"
    serial_number: str = ""
    unique_id: str = ""


# -----------------------------------------------------------------------------
# CSV and coordinate parsing
# -----------------------------------------------------------------------------


def normalize_column_name(name: str) -> str:
    return str(name).strip().lstrip("\ufeff")


# Matches: 13h31m53.5s, 13 h 31 m 53.5 s, 13:31:53.5, 13 31 53.5
_HMS_RE = re.compile(
    r"^\s*(?P<h>[+-]?\d+(?:\.\d+)?)\s*(?:h|:|\s)\s*"
    r"(?P<m>\d+(?:\.\d+)?)\s*(?:m|:|\s)\s*"
    r"(?P<s>\d+(?:\.\d+)?)\s*(?:s)?\s*$",
    re.IGNORECASE,
)

# Matches: +47d02m43.0s, +47 d 02 m 43.0 s, +47:02:43.0, +47 02 43.0
_DMS_RE = re.compile(
    r"^\s*(?P<sign>[+-]?)\s*(?P<d>\d+(?:\.\d+)?)\s*(?:d|°|:|\s)\s*"
    r"(?P<m>\d+(?:\.\d+)?)\s*(?:m|'|′|:|\s)\s*"
    r"(?P<s>\d+(?:\.\d+)?)\s*(?:s|\"|″)?\s*$",
    re.IGNORECASE,
)


def parse_ra_to_hours(value: Any) -> float:
    """Parse RA to hours for ASCOM Alpaca Telescope.SlewToCoordinatesAsync."""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("Empty RA value.")

    # Decimal numeric values: assume degrees if > 24, otherwise hours.
    try:
        x = float(text)
        if x < 0:
            raise ValueError("RA cannot be negative.")
        if x <= 24.0:
            return x % 24.0
        return (x % 360.0) / 15.0
    except ValueError:
        pass

    text2 = (
        text.replace("hours", "h")
        .replace("hour", "h")
        .replace("hrs", "h")
        .replace("hr", "h")
    )
    m = _HMS_RE.match(text2)
    if not m:
        raise ValueError(f"Cannot parse RA value: {text!r}.")

    h = float(m.group("h"))
    minute = float(m.group("m"))
    sec = float(m.group("s"))
    if h < 0 or minute < 0 or minute >= 60 or sec < 0 or sec >= 60:
        raise ValueError(f"Invalid RA value: {text!r}.")
    return (h + minute / 60.0 + sec / 3600.0) % 24.0


def parse_dec_to_degrees(value: Any) -> float:
    """Parse Dec to decimal degrees for ASCOM Alpaca Telescope.SlewToCoordinatesAsync."""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("Empty Dec value.")

    try:
        x = float(text)
        if x < -90.0 or x > 90.0:
            raise ValueError("Dec must be between -90 and +90 degrees.")
        return x
    except ValueError:
        pass

    text2 = text.replace("deg", "d").replace("degrees", "d").replace("degree", "d")
    m = _DMS_RE.match(text2)
    if not m:
        raise ValueError(f"Cannot parse Dec value: {text!r}.")

    sign = -1.0 if m.group("sign") == "-" else 1.0
    deg = float(m.group("d"))
    minute = float(m.group("m"))
    sec = float(m.group("s"))
    if deg < 0 or minute < 0 or minute >= 60 or sec < 0 or sec >= 60:
        raise ValueError(f"Invalid Dec value: {text!r}.")
    value_deg = sign * (deg + minute / 60.0 + sec / 3600.0)
    if value_deg < -90.0 or value_deg > 90.0:
        raise ValueError(f"Dec out of range: {text!r}.")
    return value_deg


def row_get(row: Dict[str, Any], key: str, fallback: str = "") -> str:
    value = row.get(key, fallback)
    if value is None:
        return fallback
    text = str(value).strip()
    return fallback if text.lower() == "nan" else text


def display_float_text(text: str, digits: int = 4) -> str:
    try:
        return f"{float(text):.{digits}f}"
    except Exception:
        return text or "—"


def resolve_csv_path(path_text: str) -> Path:
    text = path_text.strip().strip('"')
    if not text:
        raise FileNotFoundError("No CSV path was provided.")

    path = Path(text).expanduser()
    if path.is_file():
        if path.suffix.lower() != ".csv":
            raise ValueError("The selected file is not a CSV file.")
        return path

    if path.is_dir():
        csv_files = sorted(path.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csv_files:
            raise FileNotFoundError("No CSV file was found in the selected folder.")
        return csv_files[0]

    raise FileNotFoundError("The selected CSV file or folder does not exist.")


def read_targets_from_csv(path_text: str) -> Tuple[Path, List[Target], List[str]]:
    path = resolve_csv_path(path_text)
    warnings: List[str] = []
    targets: List[Target] = []

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("The CSV file has no header row.")

        original_fieldnames = list(reader.fieldnames)
        normalized = [normalize_column_name(c) for c in original_fieldnames]
        mapping = {normalize_column_name(c): c for c in original_fieldnames}

        missing_required_current = [c for c in ("center_RA_current", "center_DEC_current") if c not in mapping]
        if missing_required_current:
            raise ValueError(
                "The CSV file does not contain the required current-coordinate columns: "
                + ", ".join(missing_required_current)
                + "."
            )

        missing_useful = [c for c in REQUIRED_COLUMNS if c not in mapping]
        if missing_useful:
            warnings.append("Missing optional/useful columns: " + ", ".join(missing_useful))

        for input_index, row in enumerate(reader, start=1):
            normalized_row = {normalize_column_name(k): v for k, v in row.items()}
            ra_text = row_get(normalized_row, "center_RA_current")
            dec_text = row_get(normalized_row, "center_DEC_current")
            if not ra_text or not dec_text:
                warnings.append(f"Skipped row {input_index}: empty center_RA_current or center_DEC_current.")
                continue

            try:
                ra_hours = parse_ra_to_hours(ra_text)
                dec_deg = parse_dec_to_degrees(dec_text)
            except Exception as exc:
                warnings.append(f"Skipped row {input_index}: {exc}")
                continue

            galaxies = row_get(normalized_row, "galaxies", "")
            if not galaxies:
                galaxies = f"CSV target {input_index}"

            targets.append(
                Target(
                    row_number=input_index,
                    galaxies=galaxies,
                    ra_text=ra_text,
                    dec_text=dec_text,
                    ra_hours=ra_hours,
                    ra_degrees=ra_hours * 15.0,
                    dec_degrees=dec_deg,
                    g_star=row_get(normalized_row, "g_star"),
                    g_gal=row_get(normalized_row, "g_gal"),
                    p_raw=row_get(normalized_row, "P_raw"),
                    p_norm=row_get(normalized_row, "P_norm"),
                    klasa=row_get(normalized_row, "klasa"),
                )
            )

    if not targets:
        raise ValueError("The CSV file was loaded, but no valid targets were found.")

    return path, targets, warnings


# -----------------------------------------------------------------------------
# ASCOM Alpaca client
# -----------------------------------------------------------------------------


class AlpacaError(RuntimeError):
    pass


class AlpacaTelescope:
    def __init__(self, device: AlpacaDeviceInfo):
        self.device = device
        self.base_url = f"http://{device.host}:{device.port}/api/v1/telescope/{device.device_number}/"
        self.client_transaction_id = 0

    def _next_tx(self) -> int:
        self.client_transaction_id += 1
        return self.client_transaction_id

    def _common_params(self) -> Dict[str, Any]:
        return {
            "ClientID": CLIENT_ID,
            "ClientTransactionID": self._next_tx(),
        }

    @staticmethod
    def _check_response(response: requests.Response) -> Dict[str, Any]:
        response.raise_for_status()
        try:
            data = response.json()
        except Exception as exc:
            raise AlpacaError(f"The Alpaca device returned a non-JSON response: {response.text[:300]}") from exc

        error_number = data.get("ErrorNumber", 0)
        if error_number not in (0, None):
            raise AlpacaError(f"Alpaca error {error_number}: {data.get('ErrorMessage', '')}")
        return data

    def get(self, command: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        query = self._common_params()
        if params:
            query.update(params)
        url = urljoin(self.base_url, command.lower())
        response = requests.get(url, params=query, timeout=timeout)
        return self._check_response(response)

    def put(self, command: str, data: Optional[Dict[str, Any]] = None, timeout: float = 20.0) -> Dict[str, Any]:
        body = self._common_params()
        if data:
            body.update(data)
        url = urljoin(self.base_url, command.lower())
        response = requests.put(url, data=body, timeout=timeout)
        return self._check_response(response)

    def connect(self) -> None:
        self.put("connected", {"Connected": "true"}, timeout=20.0)

    def disconnect(self) -> None:
        self.put("connected", {"Connected": "false"}, timeout=20.0)

    def is_connected(self) -> bool:
        data = self.get("connected", timeout=10.0)
        return bool(data.get("Value"))

    def unpark_if_needed(self) -> str:
        try:
            at_park = bool(self.get("atpark", timeout=10.0).get("Value"))
        except Exception as exc:
            return f"Unpark skipped: the device did not report AtPark ({exc})."

        if not at_park:
            return "The telescope is not parked."

        try:
            self.put("unpark", timeout=20.0)
            return "Unpark command sent."
        except Exception as exc:
            return f"Unpark failed or is unsupported: {exc}."

    def enable_tracking(self) -> str:
        try:
            self.put("tracking", {"Tracking": "true"}, timeout=20.0)
            return "Tracking command sent."
        except Exception as exc:
            return f"Tracking command failed or is unsupported: {exc}."

    def slew_to_coordinates_async(self, ra_hours: float, dec_degrees: float) -> None:
        self.put(
            "slewtocoordinatesasync",
            {
                "RightAscension": f"{ra_hours:.10f}",
                "Declination": f"{dec_degrees:.10f}",
            },
            timeout=20.0,
        )

    def is_slewing(self) -> bool:
        data = self.get("slewing", timeout=10.0)
        return bool(data.get("Value"))

    def abort_slew(self) -> None:
        self.put("abortslew", timeout=10.0)

    def wait_for_slew_end(self, timeout: float = DEFAULT_GOTO_TIMEOUT_SEC) -> None:
        deadline = time.time() + timeout
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            try:
                if not self.is_slewing():
                    return
                last_error = None
            except Exception as exc:
                last_error = exc
            time.sleep(1.0)

        if last_error is not None:
            raise TimeoutError(f"Timed out while polling Slewing. Last polling error: {last_error}")
        raise TimeoutError("Timed out while waiting for the telescope slew to finish.")


def discover_alpaca_telescopes(timeout: float = DEFAULT_DISCOVERY_TIMEOUT_SEC) -> List[AlpacaDeviceInfo]:
    """Find ASCOM Alpaca telescope devices on the local network."""
    found: List[AlpacaDeviceInfo] = []
    seen: set[Tuple[str, int, int]] = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.7)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.sendto(ALPACA_DISCOVERY_MESSAGE, ("255.255.255.255", ALPACA_DISCOVERY_PORT))
        except OSError:
            # Some Windows/network configurations reject the global broadcast.
            sock.sendto(ALPACA_DISCOVERY_MESSAGE, ("<broadcast>", ALPACA_DISCOVERY_PORT))

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                payload_bytes, address = sock.recvfrom(2048)
            except socket.timeout:
                continue

            host = address[0]
            try:
                payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))
                port = int(payload.get("AlpacaPort"))
            except Exception:
                continue

            try:
                url = f"http://{host}:{port}/management/v1/configureddevices"
                response = requests.get(url, timeout=3.0)
                response.raise_for_status()
                data = response.json()
                devices = data.get("Value", [])
            except Exception:
                continue

            for dev in devices:
                device_type = str(dev.get("DeviceType", "")).lower()
                if device_type != "telescope":
                    continue
                try:
                    device_number = int(dev.get("DeviceNumber", 0))
                except Exception:
                    device_number = 0
                key = (host, port, device_number)
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    AlpacaDeviceInfo(
                        host=host,
                        port=port,
                        device_number=device_number,
                        device_name=str(dev.get("DeviceName", "ASCOM Alpaca Telescope")),
                        device_type=str(dev.get("DeviceType", "telescope")),
                        serial_number=str(dev.get("SerialNumber", "") or dev.get("Serial", "")),
                        unique_id=str(dev.get("UniqueID", "") or dev.get("UniqueId", "") or dev.get("DeviceUniqueID", "")),
                    )
                )
    finally:
        sock.close()

    return found


def enrich_alpaca_device_info(device: AlpacaDeviceInfo, telescope: AlpacaTelescope) -> None:
    """Best-effort update of device name/type/serial/ID from Alpaca metadata."""
    try:
        url = f"http://{device.host}:{device.port}/management/v1/configureddevices"
        response = requests.get(url, timeout=3.0)
        response.raise_for_status()
        devices = response.json().get("Value", [])
        for dev in devices:
            try:
                dev_number = int(dev.get("DeviceNumber", 0))
            except Exception:
                dev_number = 0
            if dev_number != device.device_number:
                continue
            if str(dev.get("DeviceType", "")).lower() != "telescope":
                continue
            device.device_name = str(dev.get("DeviceName", device.device_name) or device.device_name)
            device.device_type = str(dev.get("DeviceType", device.device_type) or device.device_type)
            device.serial_number = str(dev.get("SerialNumber", "") or dev.get("Serial", "") or device.serial_number)
            device.unique_id = str(
                dev.get("UniqueID", "")
                or dev.get("UniqueId", "")
                or dev.get("DeviceUniqueID", "")
                or device.unique_id
            )
            break
    except Exception:
        pass

    for command in ("name", "description", "driverinfo"):
        try:
            value = str(telescope.get(command, timeout=3.0).get("Value", "")).strip()
        except Exception:
            continue
        if not value:
            continue
        if command == "name" and (not device.device_name or device.device_name == "Manual Alpaca Telescope"):
            device.device_name = value
        if not device.serial_number:
            match = re.search(r"serial(?:\s+number)?\s*[:=]\s*([A-Za-z0-9_.-]+)", value, flags=re.IGNORECASE)
            if match:
                device.serial_number = match.group(1)



def format_device_for_selection(device: AlpacaDeviceInfo) -> str:
    serial_or_id = device.serial_number or device.unique_id or "not available"
    return (
        f"{device.device_name or 'ASCOM Alpaca Telescope'} | "
        f"serial/ID: {serial_or_id} | "
        f"{device.host}:{device.port} | device {device.device_number}"
    )


class SeestarSelectionDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, devices: List[AlpacaDeviceInfo]):
        super().__init__(parent)
        self.title("Select Seestar device")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.result: Optional[AlpacaDeviceInfo] = None
        self.devices = devices

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text="More than one ASCOM Alpaca telescope was detected. Select the Seestar to connect to:",
            wraplength=720,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, height=min(10, max(4, len(devices))), exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scroll.set)

        for device in devices:
            self.listbox.insert("end", format_device_for_selection(device))
        if devices:
            self.listbox.selection_set(0)
            self.listbox.activate(0)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky="e", padx=12, pady=(0, 12))
        ttk.Button(button_frame, text="Connect", command=self._accept).pack(side="left")
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side="left", padx=(8, 0))

        self.listbox.bind("<Double-Button-1>", lambda _event: self._accept())
        self.bind("<Return>", lambda _event: self._accept())
        self.bind("<Escape>", lambda _event: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")
        self.listbox.focus_set()

    def _accept(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No device selected", "Select one Seestar device first.", parent=self)
            return
        self.result = self.devices[int(selection[0])]
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


# -----------------------------------------------------------------------------
# GUI application
# -----------------------------------------------------------------------------


class ProbolismSeestarGotoBrowser:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x720")
        self.root.minsize(820, 620)

        self.csv_path_var = tk.StringVar()
        self.connection_status_var = tk.StringVar(value="Disconnected")
        self.connected_device_name_var = tk.StringVar(value="")
        self.seestar_info_var = tk.StringVar(value="Connected Seestar: not connected.")
        self.status_var = tk.StringVar(value="Ready.")
        self.auto_send_var = tk.BooleanVar(value=False)
        self.manual_host_var = tk.StringVar()
        self.manual_port_var = tk.StringVar()
        self.manual_device_var = tk.StringVar(value="0")
        self.messier_var = tk.StringVar(value=MESSIER_CATALOG[0].label if MESSIER_CATALOG else "")

        self.targets: List[Target] = []
        self.current_index: int = 0
        self.csv_path: Optional[Path] = None
        self.alpaca_device: Optional[AlpacaDeviceInfo] = None
        self.telescope: Optional[AlpacaTelescope] = None
        self.connected: bool = False
        self.busy: bool = False
        self.stop_requested: bool = False
        self.event_queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.slewing_indicator_var = tk.StringVar(value="")
        self.slewing_indicator_active: bool = False
        self.slewing_spinner_index: int = 0
        self.slewing_spinner_after_id: Optional[str] = None

        self._build_widgets()
        self._bind_keys()
        self.root.after(100, self._poll_event_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_widgets(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)

        title_bar = ttk.Frame(outer)
        title_bar.grid(row=0, column=0, sticky="ew")
        title_bar.columnconfigure(0, weight=1)
        ttk.Label(title_bar, text=APP_TITLE, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(title_bar, text="User guide", command=self.show_user_guide).grid(row=0, column=1, sticky="e")

        file_frame = ttk.LabelFrame(outer, text="Target CSV file", padding=8)
        file_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        file_frame.columnconfigure(1, weight=1)
        ttk.Label(file_frame, text="CSV file or folder:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(file_frame, textvariable=self.csv_path_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(file_frame, text="Browse CSV…", command=self.browse_csv).grid(row=0, column=2, padx=(8, 0))

        conn_frame = ttk.LabelFrame(outer, text="Seestar connection through ASCOM Alpaca", padding=8)
        conn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for col in range(8):
            conn_frame.columnconfigure(col, weight=0)
        conn_frame.columnconfigure(7, weight=1)

        self.connect_button = ttk.Button(conn_frame, text="Connect to Seestar", command=self.connect_to_seestar)
        self.connect_button.grid(row=0, column=0, sticky="w")
        self.disconnect_button = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect_from_seestar)
        self.disconnect_button.grid(row=0, column=1, padx=(8, 0), sticky="w")
        self.change_button = ttk.Button(conn_frame, text="Change Seestar", command=self.change_seestar)
        self.change_button.grid(row=0, column=2, padx=(8, 16), sticky="w")
        ttk.Label(conn_frame, text="Status:").grid(row=0, column=3, sticky="w")
        self.connection_label = ttk.Label(conn_frame, textvariable=self.connection_status_var, font=("Segoe UI", 10, "bold"))
        self.connection_label.grid(row=0, column=4, sticky="w", padx=(4, 4))
        self.connected_device_name_label = ttk.Label(conn_frame, textvariable=self.connected_device_name_var, font=("Segoe UI", 10, "bold"))
        self.connected_device_name_label.grid(row=0, column=5, columnspan=3, sticky="w", padx=(0, 18))

        ttk.Label(conn_frame, text="Manual IP:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(conn_frame, textvariable=self.manual_host_var, width=16).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(conn_frame, text="Port:").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(conn_frame, textvariable=self.manual_port_var, width=8).grid(row=1, column=3, sticky="w", pady=(8, 0))
        ttk.Label(conn_frame, text="Device:").grid(row=1, column=4, sticky="w", pady=(8, 0), padx=(12, 0))
        ttk.Entry(conn_frame, textvariable=self.manual_device_var, width=5).grid(row=1, column=5, sticky="w", pady=(8, 0))
        ttk.Label(conn_frame, text="Leave IP/Port empty to use network discovery.").grid(row=1, column=6, columnspan=2, sticky="w", padx=(12, 0), pady=(8, 0))

        ttk.Label(outer, textvariable=self.seestar_info_var, anchor="w").grid(row=3, column=0, sticky="ew", pady=(8, 0))

        target_frame = ttk.LabelFrame(outer, text="Current target", padding=10)
        target_frame.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        target_frame.columnconfigure(0, weight=1)
        self.target_title_var = tk.StringVar(value="No target loaded.")
        ttk.Label(target_frame, textvariable=self.target_title_var, font=("Segoe UI", 13, "bold"), wraplength=900).grid(row=0, column=0, sticky="w")

        details_box = ttk.Frame(target_frame)
        details_box.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        details_box.columnconfigure(0, weight=1)
        self.target_details_text = tk.Text(details_box, height=8, wrap="word", state="disabled")
        self.target_details_text.grid(row=0, column=0, sticky="ew")
        target_details_scroll = ttk.Scrollbar(details_box, orient="vertical", command=self.target_details_text.yview)
        target_details_scroll.grid(row=0, column=1, sticky="ns")
        self.target_details_text.configure(yscrollcommand=target_details_scroll.set)

        nav_frame = ttk.Frame(target_frame)
        nav_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.previous_button = ttk.Button(nav_frame, text="Previous", command=self.previous_target)
        self.previous_button.pack(side="left")
        self.next_button = ttk.Button(nav_frame, text="Next", command=self.next_target)
        self.next_button.pack(side="left", padx=(8, 0))
        self.send_button = ttk.Button(nav_frame, text="Send goto to Seestar", command=self.send_goto_to_current_target)
        self.send_button.pack(side="left", padx=(20, 0))
        self.stop_button = ttk.Button(nav_frame, text="STOP", command=self.stop_seestar_motion)
        self.stop_button.pack(side="left", padx=(36, 0))
        ttk.Checkbutton(
            nav_frame,
            text="Send goto automatically after target selection",
            variable=self.auto_send_var,
        ).pack(side="left", padx=(20, 0))

        messier_frame = ttk.Frame(target_frame)
        messier_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(messier_frame, text="Messier object:").pack(side="left")
        self.messier_combo = ttk.Combobox(
            messier_frame,
            textvariable=self.messier_var,
            values=[obj.label for obj in MESSIER_CATALOG],
            state="readonly",
            width=34,
        )
        self.messier_combo.pack(side="left", padx=(8, 0))
        self.messier_goto_button = ttk.Button(
            messier_frame,
            text="Send Messier goto to Seestar",
            command=self.send_goto_to_selected_messier,
        )
        self.messier_goto_button.pack(side="left", padx=(12, 0))
        self.slewing_indicator_label = ttk.Label(
            messier_frame,
            textvariable=self.slewing_indicator_var,
            font=("Segoe UI", 14, "bold"),
        )
        self.slewing_indicator_label.pack(side="left", padx=(36, 0))
        self._update_navigation_buttons()

        log_frame = ttk.LabelFrame(outer, text="Messages", padding=8)
        log_frame.grid(row=5, column=0, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=12, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Label(outer, textvariable=self.status_var, relief="sunken", anchor="w").grid(row=6, column=0, sticky="ew", pady=(10, 0))

    @staticmethod
    def _format_seestar_info(device: Optional[AlpacaDeviceInfo]) -> str:
        if device is None:
            return "Connected Seestar: not connected."
        serial_or_id = device.serial_number or device.unique_id or "not available"
        return (
            f"Connected Seestar: type/name: {device.device_name or 'unknown'}; "
            f"device type: {device.device_type or 'unknown'}; serial/ID: {serial_or_id}"
        )

    def _bind_keys(self) -> None:
        self.root.bind("<Left>", lambda _event: self.previous_target())
        self.root.bind("<Right>", lambda _event: self.next_target())

    def _set_target_details_text(self, text: str) -> None:
        self.target_details_text.configure(state="normal")
        self.target_details_text.delete("1.0", "end")
        self.target_details_text.insert("end", text)
        self.target_details_text.configure(state="disabled")

    def _update_navigation_buttons(self) -> None:
        state = "disabled" if self.busy else "normal"
        for button_name in (
            "previous_button",
            "next_button",
            "send_button",
            "messier_goto_button",
            "connect_button",
            "disconnect_button",
            "change_button",
        ):
            button = getattr(self, button_name, None)
            if button is not None:
                button.configure(state=state)

    @staticmethod
    def _is_below_horizon_error(text: str) -> bool:
        lower = text.lower()
        return "below" in lower and "horizon" in lower

    def log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{stamp}] {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_busy(self, busy: bool, status: Optional[str] = None) -> None:
        self.busy = busy
        self._update_navigation_buttons()
        if status:
            self.status_var.set(status)

    def _start_slewing_indicator(self) -> None:
        self.slewing_indicator_active = True
        self.slewing_spinner_index = 0
        self._animate_slewing_indicator()

    def _animate_slewing_indicator(self) -> None:
        if not self.slewing_indicator_active:
            return
        frames = "|/-\\"
        frame = frames[self.slewing_spinner_index % len(frames)]
        self.slewing_indicator_var.set(f"Slewing ... {frame}")
        self.slewing_spinner_index += 1
        self.slewing_spinner_after_id = self.root.after(250, self._animate_slewing_indicator)

    def _stop_slewing_indicator(self) -> None:
        self.slewing_indicator_active = False
        if self.slewing_spinner_after_id is not None:
            try:
                self.root.after_cancel(self.slewing_spinner_after_id)
            except Exception:
                pass
            self.slewing_spinner_after_id = None
        self.slewing_indicator_var.set("")

    def browse_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a Probolism CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.csv_path_var.set(path)
            self.load_targets()

    def load_targets(self) -> None:
        try:
            path, targets, warnings = read_targets_from_csv(self.csv_path_var.get())
            self.csv_path = path
            self.targets = targets
            self.current_index = 0
            self.display_current_target()
            self.status_var.set(f"Loaded {len(targets)} valid targets from {path.name}.")
            self.log(f"Loaded {len(targets)} valid targets from: {path}")
            for warning in warnings[:20]:
                self.log("Warning: " + warning)
            if len(warnings) > 20:
                self.log(f"Warning: {len(warnings) - 20} additional warnings were omitted from the log.")
        except Exception as exc:
            self.targets = []
            self.current_index = 0
            self.display_current_target()
            self.status_var.set("CSV load failed.")
            messagebox.showerror("Cannot load targets", str(exc))
            self.log(f"CSV load error: {exc}")

    def display_current_target(self) -> None:
        if not self.targets:
            self.target_title_var.set("No target loaded.")
            self._set_target_details_text("Choose and load a Probolism CSV file.")
            return

        target = self.targets[self.current_index]
        self.target_title_var.set(f"Target {self.current_index + 1} of {len(self.targets)}")
        self._set_target_details_text(
            f"Galaxies: {target.galaxies}\n\n"
            "Coordinates used for GoTo:\n"
            f"  center_RA_current:  {target.ra_text}  ({target.ra_hours:.8f} h, {target.ra_degrees:.6f} deg)\n"
            f"  center_DEC_current: {target.dec_text}  ({target.dec_degrees:.6f} deg)\n\n"
            "CSV metrics:\n"
            f"  g_star: {target.g_star or '—'}    g_gal: {target.g_gal or '—'}    "
            f"P_raw: {display_float_text(target.p_raw)}    P_norm: {display_float_text(target.p_norm)}    "
            f"class: {target.klasa or '—'}"
        )
        self.status_var.set(f"Selected target {self.current_index + 1} of {len(self.targets)}.")

    def previous_target(self) -> None:
        if not self.targets:
            self.root.bell()
            return
        if self.busy:
            self.root.bell()
            self.log("Navigation ignored: a connection or GoTo operation is still running.")
            return
        self.current_index = (self.current_index - 1) % len(self.targets)
        self.display_current_target()
        if self.auto_send_var.get():
            self.send_goto_to_current_target()

    def next_target(self) -> None:
        if not self.targets:
            self.root.bell()
            return
        if self.busy:
            self.root.bell()
            self.log("Navigation ignored: a connection or GoTo operation is still running.")
            return
        self.current_index = (self.current_index + 1) % len(self.targets)
        self.display_current_target()
        if self.auto_send_var.get():
            self.send_goto_to_current_target()

    def _manual_device_info(self) -> Optional[AlpacaDeviceInfo]:
        host = self.manual_host_var.get().strip()
        port_text = self.manual_port_var.get().strip()
        if not host and not port_text:
            return None
        if not host or not port_text:
            raise ValueError("Both Manual IP and Port must be filled, or both must be empty for discovery.")
        try:
            port = int(port_text)
        except Exception:
            raise ValueError("Manual Port must be an integer.")
        if port <= 0 or port > 65535:
            raise ValueError("Manual Port must be between 1 and 65535.")
        try:
            device_number = int(self.manual_device_var.get().strip() or "0")
        except Exception:
            raise ValueError("Manual Device must be an integer.")
        if device_number < 0:
            raise ValueError("Manual Device must be zero or a positive integer.")
        return AlpacaDeviceInfo(host=host, port=port, device_number=device_number, device_name="Manual Alpaca Telescope", device_type="telescope")

    def connect_to_seestar(self) -> None:
        if self.busy:
            self.root.bell()
            return
        if self.connected:
            messagebox.showinfo("Already connected", "The program is already connected to an Alpaca telescope. Use Change Seestar to select another device.")
            return

        try:
            manual = self._manual_device_info()
        except Exception as exc:
            messagebox.showerror("Invalid manual connection settings", str(exc))
            return

        if manual is not None:
            self._start_connect_to_device(manual)
        else:
            self._start_discovery_for_selection(close_current=False)

    def change_seestar(self) -> None:
        if self.busy:
            self.root.bell()
            return
        self._start_discovery_for_selection(close_current=True)

    def _start_discovery_for_selection(self, close_current: bool) -> None:
        self.set_busy(True, "Searching for Seestars…")
        self.connection_status_var.set("Searching…" if not close_current else "Changing…")
        if close_current:
            self.log("Changing Seestar: disconnecting from the current device and searching again…")
        else:
            self.log("Searching for ASCOM Alpaca telescopes on the local network…")
        thread = threading.Thread(target=self._discover_devices_worker, args=(close_current,), daemon=True)
        thread.start()

    def _discover_devices_worker(self, close_current: bool) -> None:
        try:
            if close_current and self.telescope:
                try:
                    self.telescope.disconnect()
                except Exception:
                    pass
            devices = discover_alpaca_telescopes(DEFAULT_DISCOVERY_TIMEOUT_SEC)
            if not devices:
                raise RuntimeError(
                    "No ASCOM Alpaca telescope was found on the local network. "
                    "Check Station Mode, Wi-Fi, Windows Firewall, router client isolation, or enter IP and port manually."
                )
            self.event_queue.put(("select_device", (devices, close_current)))
        except Exception as exc:
            self.event_queue.put(("connect_error", f"{exc}\n\n{traceback.format_exc(limit=4)}"))

    def _start_connect_to_device(self, device: AlpacaDeviceInfo) -> None:
        self.set_busy(True, "Connecting to Seestar…")
        self.connection_status_var.set("Connecting…")
        self.log(f"Connecting to: {format_device_for_selection(device)}")
        thread = threading.Thread(target=self._connect_worker, args=(device,), daemon=True)
        thread.start()

    def _connect_worker(self, device: AlpacaDeviceInfo) -> None:
        try:
            telescope = AlpacaTelescope(device)
            telescope.connect()
            connected = telescope.is_connected()
            if not connected:
                raise RuntimeError("The telescope did not report Connected = true after the connect command.")

            enrich_alpaca_device_info(device, telescope)
            unpark_message = telescope.unpark_if_needed()
            tracking_message = telescope.enable_tracking()
            self.event_queue.put(("connected", (device, telescope, unpark_message, tracking_message)))
        except Exception as exc:
            self.event_queue.put(("connect_error", f"{exc}\n\n{traceback.format_exc(limit=4)}"))

    def disconnect_from_seestar(self) -> None:
        if self.busy:
            self.root.bell()
            return
        if not self.telescope:
            self.connected = False
            self.connection_status_var.set("Disconnected")
            self.connected_device_name_var.set("")
            self.seestar_info_var.set(self._format_seestar_info(None))
            self.status_var.set("Disconnected.")
            return

        self.set_busy(True, "Disconnecting…")
        self.log("Disconnecting from Alpaca telescope…")
        thread = threading.Thread(target=self._disconnect_worker, daemon=True)
        thread.start()

    def _disconnect_worker(self) -> None:
        try:
            if self.telescope:
                self.telescope.disconnect()
            self.event_queue.put(("disconnected", None))
        except Exception as exc:
            self.event_queue.put(("disconnect_error", f"{exc}\n\n{traceback.format_exc(limit=4)}"))

    def send_goto_to_current_target(self) -> None:
        if not self.targets:
            messagebox.showinfo("No target loaded", "Load a CSV target list first.")
            return
        target = self.targets[self.current_index]
        label = f"target {self.current_index + 1}"
        self._start_goto(target, label, target.galaxies)

    def _selected_messier_object(self) -> Optional[MessierObject]:
        selected = self.messier_var.get().strip()
        for obj in MESSIER_CATALOG:
            if obj.label == selected:
                return obj
        return None

    def send_goto_to_selected_messier(self) -> None:
        obj = self._selected_messier_object()
        if obj is None:
            messagebox.showerror("No Messier object selected", "Select a Messier object from the list first.")
            return
        self._start_goto(obj, obj.label, obj.label)

    def _start_goto(self, target: Any, label: str, target_name: str) -> None:
        if self.busy:
            self.root.bell()
            self.log("GoTo request ignored: another operation is still running.")
            return
        if not self.connected or not self.telescope:
            messagebox.showerror("Not connected", "Connect to Seestar before sending a GoTo command.")
            return

        self.stop_requested = False
        self.set_busy(True, f"Sending GoTo to {label}…")
        self._start_slewing_indicator()
        self.log(
            f"Sending GoTo: {label}, "
            f"RA={target.ra_hours:.8f} h, Dec={target.dec_degrees:.6f} deg, name={target_name}"
        )
        thread = threading.Thread(target=self._goto_worker, args=(target, label, target_name), daemon=True)
        thread.start()

    def stop_seestar_motion(self) -> None:
        if not self.connected or not self.telescope:
            messagebox.showerror("Not connected", "Connect to Seestar before sending STOP.")
            return
        self.stop_requested = True
        self.status_var.set("Sending STOP to Seestar…")
        self.log("STOP requested: sending AbortSlew to Seestar.")
        thread = threading.Thread(target=self._stop_worker, daemon=True)
        thread.start()

    def _stop_worker(self) -> None:
        try:
            if not self.telescope:
                raise RuntimeError("No telescope object is available.")
            self.telescope.abort_slew()
            self.event_queue.put(("stop_done", None))
        except Exception as exc:
            self.event_queue.put(("stop_error", f"{exc}\n\n{traceback.format_exc(limit=4)}"))

    def _goto_worker(self, target: Any, label: str, target_name: str) -> None:
        try:
            if not self.telescope:
                raise RuntimeError("No telescope object is available.")
            self.telescope.slew_to_coordinates_async(target.ra_hours, target.dec_degrees)
            self.telescope.wait_for_slew_end(DEFAULT_GOTO_TIMEOUT_SEC)
            if self.stop_requested:
                self.event_queue.put(("goto_stopped", (label, target_name)))
            else:
                self.event_queue.put(("goto_done", (label, target_name)))
        except Exception as exc:
            self.event_queue.put(("goto_error", f"{exc}\n\n{traceback.format_exc(limit=4)}"))

    def _poll_event_queue(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "select_device":
                    devices, old_connection_closed = payload
                    if old_connection_closed:
                        self.alpaca_device = None
                        self.telescope = None
                        self.connected = False
                        self.connection_status_var.set("Disconnected")
                        self.connected_device_name_var.set("")
                        self.seestar_info_var.set(self._format_seestar_info(None))
                    if len(devices) == 1:
                        self._start_connect_to_device(devices[0])
                    else:
                        self.set_busy(False, "Select a Seestar from the detected devices.")
                        dialog = SeestarSelectionDialog(self.root, devices)
                        self.root.wait_window(dialog)
                        if dialog.result is None:
                            self.connection_status_var.set("Disconnected" if old_connection_closed or not self.connected else "Connected")
                            self.status_var.set("Device selection cancelled.")
                            self.log("Device selection cancelled.")
                        else:
                            self._start_connect_to_device(dialog.result)
                elif kind == "connected":
                    device, telescope, unpark_message, tracking_message = payload
                    self.alpaca_device = device
                    self.telescope = telescope
                    self.connected = True
                    self.connection_status_var.set("Connected")
                    self.connected_device_name_var.set(device.device_name or "ASCOM Alpaca Telescope")
                    self.seestar_info_var.set(self._format_seestar_info(device))
                    self.manual_host_var.set(device.host)
                    self.manual_port_var.set(str(device.port))
                    self.manual_device_var.set(str(device.device_number))
                    self.set_busy(False, "Connected to Seestar.")
                    self.log(
                        f"Connected: {device.device_name} at {device.host}:{device.port}, device {device.device_number}."
                    )
                    self.log(unpark_message)
                    self.log(tracking_message)
                elif kind == "connect_error":
                    self.alpaca_device = None
                    self.telescope = None
                    self.connected = False
                    self.connection_status_var.set("Disconnected")
                    self.connected_device_name_var.set("")
                    self.seestar_info_var.set(self._format_seestar_info(None))
                    self.set_busy(False, "Connection failed.")
                    messagebox.showerror("Connection failed", str(payload))
                    self.log("Connection failed: " + str(payload).splitlines()[0])
                elif kind == "disconnected":
                    self.alpaca_device = None
                    self.telescope = None
                    self.connected = False
                    self.connection_status_var.set("Disconnected")
                    self.connected_device_name_var.set("")
                    self.seestar_info_var.set(self._format_seestar_info(None))
                    self.set_busy(False, "Disconnected.")
                    self.log("Disconnected.")
                elif kind == "disconnect_error":
                    self.alpaca_device = None
                    self.telescope = None
                    self.connected = False
                    self.connection_status_var.set("Disconnected")
                    self.connected_device_name_var.set("")
                    self.seestar_info_var.set(self._format_seestar_info(None))
                    self.set_busy(False, "Disconnect reported an error; local state was reset.")
                    messagebox.showwarning("Disconnect error", str(payload))
                    self.log("Disconnect error: " + str(payload).splitlines()[0])
                elif kind == "goto_done":
                    label, target_name = payload
                    self.stop_requested = False
                    self._stop_slewing_indicator()
                    self.set_busy(False, f"GoTo completed for {label}.")
                    self.log(f"GoTo completed: {label}, {target_name}")
                    self.log("Use the Seestar app to observe the object and make framing corrections.")
                elif kind == "goto_stopped":
                    label, target_name = payload
                    self.stop_requested = False
                    self._stop_slewing_indicator()
                    self.set_busy(False, f"GoTo stopped for {label}.")
                    self.log(f"GoTo stopped: {label}, {target_name}")
                elif kind == "goto_error":
                    self.stop_requested = False
                    self._stop_slewing_indicator()
                    self.set_busy(False, "GoTo failed.")
                    if self._is_below_horizon_error(str(payload)):
                        messagebox.showerror("Target below horizon", "The object is below the horizon.")
                    else:
                        messagebox.showerror("GoTo failed", str(payload))
                    self.log("GoTo failed: " + str(payload).splitlines()[0])
                elif kind == "stop_done":
                    self.status_var.set("STOP command sent.")
                    self.log("STOP command sent successfully.")
                elif kind == "stop_error":
                    messagebox.showerror("STOP failed", str(payload))
                    self.log("STOP failed: " + str(payload).splitlines()[0])
        except queue.Empty:
            pass
        self.root.after(100, self._poll_event_queue)

    def show_user_guide(self) -> None:
        guide = """Probolism Seestar simple goto browser v1_4 by piotrs — user guide

Purpose
-------
This program reads a Probolism CSV file and lets you browse its targets. It can send a simple ASCOM Alpaca GoTo command to a Seestar telescope for the currently selected CSV target. It can also send GoTo commands to selected objects from the built-in Messier catalogue. Messier GoTo can be used without loading a CSV file first.

What this program does
----------------------
1. Loads targets from a CSV file generated by the Probolism CSV browser/calculation workflow.
2. Uses center_RA_current and center_DEC_current as the CSV GoTo coordinates.
3. Shows the target number and the galaxies field for the current CSV target.
4. Uses the left/right arrow keys or the Previous/Next buttons to browse CSV targets.
5. Sends GoTo commands to a Seestar through ASCOM Alpaca over Wi-Fi.
6. Shows long current-target descriptions in a fixed, scrollable Current target box.
7. Disables Previous, Next, Send goto to Seestar, Send Messier goto to Seestar, Connect to Seestar, Disconnect, and Change Seestar while a GoTo operation is running.
8. Shows a large "Slewing ..." indicator with an ASCII spinner while the telescope is moving.
9. Provides a STOP button that sends AbortSlew to interrupt telescope motion.
10. Shows the connected Seestar name next to the Connected status.
11. Writes detected connection data into Manual IP, Port, and Device after a successful connection.
12. Shows the connected Seestar type/name and serial/ID above the Current target box, when that information is available.
13. If more than one ASCOM Alpaca telescope is detected, shows a selection dialog so you can choose which Seestar to connect to.
14. Provides Change Seestar to disconnect from the current Seestar and choose another detected Seestar.
15. Provides a Messier object drop-down list with descriptive names and a Send Messier goto to Seestar button.
16. Automatically disconnects from Seestar when the program window is closed.

What this program does not do
-----------------------------
It does not perform plate solving, centering, focusing, stacking, or image capture. It only sends simple GoTo commands. After GoTo is complete, use the Seestar app to observe the object and make framing corrections.

Typical use with CSV targets
----------------------------
1. Turn on the Seestar.
2. Use the Seestar app to connect the Seestar to your home Wi-Fi in Station Mode.
3. Connect this Windows computer to the same Wi-Fi network.
4. Start this program.
5. Choose the CSV file with Browse CSV. The file is loaded immediately after selection.
6. Click Connect to Seestar.
7. If more than one Seestar is detected, select the device in the dialog and click Connect.
8. Select a CSV target with the right/left arrow keys or with Previous/Next.
9. Click Send goto to Seestar.
10. Wait until the GoTo is complete. During telescope motion, the navigation, GoTo, connect, disconnect, and change-device buttons are disabled, and the Slewing indicator is visible.
11. If you need to interrupt telescope movement, click STOP.
12. After GoTo is complete, use the Seestar app to observe the object and make framing corrections.
13. Closing the program window automatically sends Disconnect to Seestar when a connection is active.

Using the Seestar app at the same time
--------------------------------------
It is possible to have this program and the Seestar app connected to the same Seestar at the same time. The recommended workflow is to use this program for simple GoTo commands and use the Seestar app for observation, framing corrections, imaging, stacking, and other Seestar-specific functions. Avoid sending conflicting movement commands from both places at the same time.

Changing Seestar
----------------
Click Change Seestar when you want to connect to another Seestar. The program first sends Disconnect to the currently connected Seestar, then searches the local network again. If more than one ASCOM Alpaca telescope is detected, the program shows a selection dialog. Select the desired device and click Connect. If you cancel the selection after changing devices, the previous Seestar remains disconnected.

Messier catalogue GoTo
----------------------
Use the Messier object drop-down list to select a Messier object. The list includes descriptive object names, such as M31 - Andromeda Galaxy or M42 - Orion Nebula. Click Send Messier goto to Seestar to send a GoTo command to that object. The Messier GoTo does not require a loaded CSV file and does not change the currently selected CSV target. The built-in Messier coordinates are approximate J2000.0 catalogue coordinates.

Automatic send mode
-------------------
If "Send goto automatically after target selection" is checked, the program sends a GoTo command immediately after you select another CSV target with Previous/Next or the left/right arrow keys. Use this mode carefully. This automatic mode applies to CSV target browsing, not to the Messier drop-down list.

Manual IP, port, and device
---------------------------
Leave Manual IP and Port empty to use ASCOM Alpaca network discovery. If discovery does not find the Seestar, enter its IP address and Alpaca port manually, then click Connect to Seestar again.

After a successful connection, the program fills Manual IP, Port, and Device with the detected Alpaca connection data. It also shows the connected Seestar name next to the Connected status and shows type/name plus serial/ID above the Current target box when the Alpaca device reports that information.

STOP button
-----------
The STOP button sends the ASCOM Alpaca AbortSlew command. Use it to interrupt Seestar movement. The STOP button remains available while the telescope is slewing.

Building an EXE without a terminal window
-----------------------------------------
When compiling this program to a Windows EXE with PyInstaller, build it with the --noconsole option, for example:

  pyinstaller --onefile --noconsole probolism_seestar_simple_goto_browser_v1_4_by_piotrs.py

This produces a GUI EXE that does not open a separate terminal window.

Troubleshooting
---------------
No CSV file found:
  Choose an existing CSV file. If you select a folder, the program uses the newest CSV file in that folder. Loading a CSV is not required for Messier catalogue GoTo.

CSV columns missing:
  The required columns are center_RA_current and center_DEC_current. The useful display columns are galaxies, g_star, g_gal, P_raw, P_norm, and klasa.

No Alpaca telescope found:
  Check that the Seestar is on, in Station Mode, and connected to the same Wi-Fi network as this computer. Also check Windows Firewall and router client isolation.

More than one Seestar detected:
  Select the desired device in the selection dialog. The dialog shows device name, serial/ID if available, IP, port, and Alpaca device number.

Target below horizon:
  If the Alpaca telescope reports that the selected target is below the horizon, the program shows only this warning: "The object is below the horizon."

GoTo failed:
  Check that the telescope is connected, initialized, and allowed to slew. The Seestar firmware/Alpaca implementation must support SlewToCoordinatesAsync.

STOP failed:
  Check that the Seestar is still connected and that its Alpaca implementation supports AbortSlew.

Authorship
----------
© 2026 piotrs. All rights reserved. This program was developed by the author with the use of AI tools, including ChatGPT, as support in creating and improving the code.
"""
        window = tk.Toplevel(self.root)
        window.title("User guide")
        window.transient(self.root)
        window.resizable(True, True)
        width = max(820, min(1100, self.root.winfo_width()))
        height = max(620, min(850, self.root.winfo_height()))
        x = self.root.winfo_rootx() + 30
        y = self.root.winfo_rooty() + 30
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        frame = ttk.Frame(window, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text_widget = tk.Text(frame, wrap="word")
        text_widget.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=scroll.set)
        text_widget.insert("1.0", guide)
        text_widget.configure(state="disabled")

        ttk.Button(frame, text="Close", command=window.destroy).grid(row=1, column=0, columnspan=2, sticky="e", pady=(8, 0))

    def on_close(self) -> None:
        self._stop_slewing_indicator()
        if self.telescope:
            try:
                self.telescope.disconnect()
            except Exception:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    # Better default scaling on many Windows displays.
    try:
        root.tk.call("tk", "scaling", 1.1)
    except Exception:
        pass
    app = ProbolismSeestarGotoBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main()

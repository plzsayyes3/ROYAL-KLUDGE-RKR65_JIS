#!/usr/bin/env python3
"""Map the base-layer key immediately right of L to the HID hyphen key."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VID = 0x258A
PID = 0x01F7
USAGE_PAGE = 0xFF00
USAGE = 0x0001
REPORT_ID = 0x06
REPORT_LENGTH = 519
RESPONSE_HEADER = bytes([0x06, 0x83, 0x00, 0x00, 0x01, 0x00, 0xF8, 0x01])
WRITE_HEADER = bytes([0x03, 0x00, 0x00, 0x01, 0x00, 0xF8, 0x01])
TARGET_SLOT = 63  # physical key immediately right of L: ; / +
EXPECTED_SEMICOLON = bytes([0x00, 0x00, 0x00, 0x33])
HID_HYPHEN = bytes([0x00, 0x00, 0x00, 0x2D])


def build_write(backup: dict) -> bytes:
    if backup.get("format") != "rk65-beiying-matrix-backup-v1":
        raise ValueError("Unsupported backup format")
    raw = backup.get("responseBytes")
    if not isinstance(raw, list) or len(raw) != 512:
        raise ValueError("Backup must contain exactly 512 response bytes")
    if any(not isinstance(value, int) or not 0 <= value <= 255 for value in raw):
        raise ValueError("Backup contains an invalid byte value")
    response = bytes(raw)
    if response[:8] != RESPONSE_HEADER:
        raise ValueError("Expected a layer-0 matrix response")
    matrix = bytearray(response[8:])
    offset = TARGET_SLOT * 4
    current = bytes(matrix[offset : offset + 4])
    if current != EXPECTED_SEMICOLON:
        raise ValueError(
            f"slot {TARGET_SLOT} is not the expected ; key code: {current.hex(' ').upper()}"
        )
    matrix[offset : offset + 4] = HID_HYPHEN
    request = bytearray(REPORT_LENGTH)
    request[:7] = WRITE_HEADER
    request[7 : 7 + len(matrix)] = matrix
    return bytes(request)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path, help="JSON backup from beiying_read_probe.py")
    parser.add_argument("--write", action="store_true", help="send the base-layer payload")
    args = parser.parse_args()
    try:
        backup = json.loads(args.backup.read_text(encoding="utf-8"))
        request = build_write(backup)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"source-backup: {args.backup.resolve()}")
    print(f"target: Gaming Keyboard VID=0x{VID:04X} PID=0x{PID:04X}, base layer=0")
    print(f"slot {TARGET_SLOT} (; / +, immediately right of L): 00 00 00 33 -> 00 00 00 2D (HID hyphen)")
    print("all other base-layer bytes: unchanged from the read-only backup")
    if not args.write:
        print("dry-run only; no HID reports sent")
        return 0

    phrase = "WRITE RK65 BASE HYPHEN KEY"
    print(f"This sends one complete base-layer write. Type exactly: {phrase}")
    if input("> ").strip() != phrase:
        print("cancelled; no HID reports sent")
        return 4

    try:
        import hid
    except ImportError:
        print("hidapi is missing. Install it with: python3 -m pip install hidapi", file=sys.stderr)
        return 2

    matches = [
        item
        for item in hid.enumerate(VID, PID)
        if item.get("usage_page") == USAGE_PAGE and item.get("usage") == USAGE
    ]
    if len(matches) != 1:
        print(f"Expected exactly one RK configuration interface; found {len(matches)}", file=sys.stderr)
        return 3

    device = hid.device()
    try:
        device.open_path(matches[0]["path"])
        sent = device.send_feature_report(bytes([REPORT_ID]) + request)
        if sent != REPORT_LENGTH + 1:
            print(f"WRITE FAILED: short HID transfer ({sent}/{REPORT_LENGTH + 1} bytes)", file=sys.stderr)
            return 5
        print(f"WRITE SENT: layer=0 slot={TARGET_SLOT} HID hyphen; bytes={sent}")
        return 0
    except Exception as exc:  # HIDAPI errors vary by platform.
        print(f"WRITE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 5
    finally:
        device.close()


if __name__ == "__main__":
    raise SystemExit(main())

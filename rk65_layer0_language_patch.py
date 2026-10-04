#!/usr/bin/env python3
"""Set the space-adjacent base-layer keys to LANG2 and LANG1.

Uses a read-only RK65 backup as the source matrix, then patches only slot 23
(left of Space) and slot 41 (right of Space). Dry-run is the default.
"""

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
LEFT_SLOT = 23
SPACE_SLOT = 35
RIGHT_SLOT = 41
LANG2 = bytes([0x00, 0x00, 0x00, 0x91])
LANG1 = bytes([0x00, 0x00, 0x00, 0x90])
EXPECTED_LEFT = bytes([0x00, 0x00, 0x00, 0x8B])
EXPECTED_RIGHT = bytes([0x00, 0x00, 0x00, 0x8A])


def slot_offset(slot: int) -> int:
    return slot * 4


def parse_backup(backup: dict) -> bytes:
    if backup.get("format") != "rk65-beiying-matrix-backup-v1":
        raise ValueError("Unsupported backup format")
    raw = backup.get("responseBytes")
    if not isinstance(raw, list) or len(raw) != 512:
        raise ValueError("Backup must contain exactly 512 response bytes")
    if any(not isinstance(value, int) or not 0 <= value <= 255 for value in raw):
        raise ValueError("Backup contains an invalid byte value")
    response = bytes(raw)
    if response[:8] != RESPONSE_HEADER:
        raise ValueError(f"Unexpected layer-0 matrix response header: {response[:8].hex(' ')}")
    return response


def build_layer0_write(response: bytes | bytearray) -> bytes:
    if len(response) != 512 or bytes(response[:8]) != RESPONSE_HEADER:
        raise ValueError("Expected the complete layer-0 matrix response")
    matrix = bytearray(response[8:])
    left = matrix[slot_offset(LEFT_SLOT) : slot_offset(LEFT_SLOT) + 4]
    right = matrix[slot_offset(RIGHT_SLOT) : slot_offset(RIGHT_SLOT) + 4]
    if left != EXPECTED_LEFT or right != EXPECTED_RIGHT:
        raise ValueError(
            "Space-neighbor codes differ from the inspected snapshot; "
            f"slot 23={left.hex(' ').upper()}, slot 41={right.hex(' ').upper()}"
        )
    matrix[slot_offset(LEFT_SLOT) : slot_offset(LEFT_SLOT) + 4] = LANG2
    matrix[slot_offset(RIGHT_SLOT) : slot_offset(RIGHT_SLOT) + 4] = LANG1
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
        response = parse_backup(backup)
        request = build_layer0_write(response)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"source-backup: {args.backup.resolve()}")
    print(f"target: Gaming Keyboard VID=0x{VID:04X} PID=0x{PID:04X}, base layer=0")
    print(f"slot {LEFT_SLOT} (left of Space): 00 00 00 8B -> {LANG2.hex(' ').upper()} (LANG2)")
    print(f"slot {RIGHT_SLOT} (right of Space): 00 00 00 8A -> {LANG1.hex(' ').upper()} (LANG1)")
    print(f"Space slot {SPACE_SLOT}: {bytes(response[8 + slot_offset(SPACE_SLOT):12 + slot_offset(SPACE_SLOT)]).hex(' ').upper()} (unchanged)")
    print("all other base-layer bytes: unchanged from the read-only backup")
    if not args.write:
        print("dry-run only; no HID reports sent")
        return 0

    phrase = "WRITE RK65 BASE LANG PAIR"
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
        print(f"WRITE SENT: layer=0 slot={LEFT_SLOT} LANG2, slot={RIGHT_SLOT} LANG1; bytes={sent}; no readback")
        return 0
    except Exception as exc:  # HIDAPI errors vary by platform.
        print(f"WRITE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 5
    finally:
        device.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Patch Fn+M to the LANG1 code using a captured RK65 HID write log.

The program does not attempt to read the Fn layer from the keyboard. It patches
the most recent complete layer-1 SetFeature payload in the supplied log. By
default it only previews; pass --write to send the full layer to the device.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VID = 0x258A
PID = 0x01F7
USAGE_PAGE = 0xFF00
USAGE = 0x0001
REPORT_ID = 0x06
REPORT_LENGTH = 519
LAYER_HEADER_LENGTH = 7
M_SLOT = 46
V_SLOT = 28
MUHENKAN_SLOT = 23
LANG1_SLOT = 41
LANG1 = bytes([0x00, 0x00, 0x00, 0x8A])
LANG2 = bytes([0x00, 0x00, 0x00, 0x8B])
FN_M_A = bytes([0x00, 0x00, 0x00, 0x04])
FEATURE_LINE = re.compile(r"SetFeature\s*\[519\]\s*bytes\s*->\s*([\d,\s]+)")


def _slot_offset(slot: int) -> int:
    if not 0 <= slot < (REPORT_LENGTH - LAYER_HEADER_LENGTH) // 4:
        raise ValueError(f"Invalid key slot: {slot}")
    return LAYER_HEADER_LENGTH + slot * 4


def extract_latest_layer(log_text: str, layer: int) -> bytes:
    """Return the last complete 519-byte command-0x03 payload for `layer`."""
    found = None
    for match in FEATURE_LINE.finditer(log_text):
        values = [int(part.strip()) for part in match.group(1).split(",") if part.strip()]
        if len(values) != REPORT_LENGTH or any(value > 255 for value in values):
            continue
        payload = bytes(values)
        if payload[0] == 0x03 and payload[1] == layer:
            found = payload
    if found is None:
        raise ValueError(f"No complete layer-{layer} SetFeature payload found in log")
    expected_header = bytes([0x03, layer, 0x00, 0x01, 0x00, 0xF8, 0x01])
    if found[:LAYER_HEADER_LENGTH] != expected_header:
        raise ValueError(f"Unexpected layer-{layer} header: {found[:7].hex(' ')}")
    return found


def build_layer_write(source: bytes | bytearray, mappings: dict[int, bytes]) -> bytes:
    if len(source) != REPORT_LENGTH:
        raise ValueError(f"Expected {REPORT_LENGTH} payload bytes, got {len(source)}")
    if source[0] != 0x03 or source[1] != 1:
        raise ValueError("Source payload is not a layer-1 write")
    result = bytearray(source)
    for slot, value in mappings.items():
        if len(value) != 4:
            raise ValueError("A key mapping must be exactly four bytes")
        offset = _slot_offset(slot)
        result[offset : offset + 4] = value
    return bytes(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="text file containing the captured Windows HID log")
    parser.add_argument(
        "--write",
        action="store_true",
        help="send the patched full Fn-layer payload (default is preview only)",
    )
    args = parser.parse_args()

    try:
        log_text = args.log.read_text(encoding="utf-8", errors="replace")
        layer1 = extract_latest_layer(log_text, 1)
        layer0 = extract_latest_layer(log_text, 0)
        base_lang2 = layer0[_slot_offset(MUHENKAN_SLOT) : _slot_offset(MUHENKAN_SLOT) + 4]
        base_lang1 = layer0[_slot_offset(LANG1_SLOT) : _slot_offset(LANG1_SLOT) + 4]
        if base_lang2 != LANG2:
            raise ValueError(
                "Captured layer-0 slot 23 is not the expected LANG2 code "
                f"00 00 00 8B (found {base_lang2.hex(' ').upper()}); refusing to guess"
            )
        if base_lang1 != LANG1:
            raise ValueError(
                "Captured layer-0 slot 41 is not the expected LANG1 code "
                f"00 00 00 8A (found {base_lang1.hex(' ').upper()}); refusing to guess"
            )
        old = layer1[_slot_offset(M_SLOT) : _slot_offset(M_SLOT) + 4]
        if old != FN_M_A:
            raise ValueError(
                "Captured Fn+M slot 46 is not A (00 00 00 04); "
                f"found {old.hex(' ').upper()}, refusing to patch a mismatched snapshot"
            )
        old_v = layer1[_slot_offset(V_SLOT) : _slot_offset(V_SLOT) + 4]
        patched = build_layer_write(layer1, {M_SLOT: LANG1, V_SLOT: LANG2})
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    offset = _slot_offset(M_SLOT)
    print(f"source-log: {args.log.resolve()}")
    print("target: Gaming Keyboard VID=0x258A PID=0x01F7, layer=1")
    print(f"Fn+M slot {M_SLOT}: {old.hex(' ').upper()} -> {LANG1.hex(' ').upper()} (LANG1)")
    print(f"Fn+V slot {V_SLOT}: {old_v.hex(' ').upper()} -> {LANG2.hex(' ').upper()} (LANG2)")
    print("other Fn-layer bytes: unchanged from the latest captured layer-1 payload")
    print("NOTE: the full Fn layer comes from this log; changes made after capture may be overwritten.")
    print(f"patched-slot-offset: {offset}; payload-length: {len(patched)}")
    if not args.write:
        print("dry-run only; no device was opened and no HID reports were sent")
        return 0

    phrase = "WRITE RK65 PID 01F7"
    print(f"This sends one complete layer-1 write. Type exactly: {phrase}")
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
        sent = device.send_feature_report(bytes([REPORT_ID]) + patched)
        if sent != REPORT_LENGTH + 1:
            print(f"WRITE FAILED: short HID transfer ({sent}/{REPORT_LENGTH + 1} bytes)", file=sys.stderr)
            return 5
        print(f"WRITE SENT: layer=1 slot={M_SLOT} LANG1; bytes={sent}; no readback performed")
        return 0
    except Exception as exc:  # HIDAPI errors vary by platform.
        print(f"WRITE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 5
    finally:
        device.close()


if __name__ == "__main__":
    raise SystemExit(main())

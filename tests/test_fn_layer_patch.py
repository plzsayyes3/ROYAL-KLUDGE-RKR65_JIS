import unittest

from rk65_fn_layer_patch import (
    LANG1,
    LANG2,
    M_SLOT,
    V_SLOT,
    REPORT_LENGTH,
    build_layer_write,
    extract_latest_layer,
)


def feature_line(layer, slots=None):
    request = bytearray(REPORT_LENGTH)
    request[:7] = bytes([0x03, layer, 0, 1, 0, 0xF8, 1])
    for slot, value in (slots or {}).items():
        request[7 + slot * 4 : 11 + slot * 4] = bytes(value)
    return "SetFeature [519] bytes -> " + ",".join(map(str, request))


class FnLayerPatchTests(unittest.TestCase):
    def test_extracts_latest_layer_one_write_only(self):
        log = "\n".join(
            [
                feature_line(0, {M_SLOT: [0, 0, 0, 0x10]}),
                feature_line(1, {M_SLOT: [0, 0, 0, 0x04]}),
                feature_line(0, {M_SLOT: [0, 0, 0, 0x10]}),
            ]
        )
        source = extract_latest_layer(log, 1)
        self.assertEqual(source[7 + M_SLOT * 4 : 11 + M_SLOT * 4], bytes([0, 0, 0, 4]))

    def test_patches_fn_m_and_fn_v_and_preserves_other_slots(self):
        source = bytearray(
            map(
                int,
                feature_line(1, {2: [1, 2, 3, 4], M_SLOT: [0, 0, 0, 4]})
                .split("-> ", 1)[1]
                .split(","),
            )
        )
        result = build_layer_write(source, {M_SLOT: LANG1, V_SLOT: LANG2})
        offset = 7 + M_SLOT * 4
        self.assertEqual(result[:7], bytes([3, 1, 0, 1, 0, 0xF8, 1]))
        self.assertEqual(result[offset : offset + 4], LANG1)
        v_offset = 7 + V_SLOT * 4
        self.assertEqual(result[v_offset : v_offset + 4], LANG2)
        self.assertEqual(result[7 + 2 * 4 : 11 + 2 * 4], bytes([1, 2, 3, 4]))

    def test_rejects_missing_layer(self):
        with self.assertRaises(ValueError):
            extract_latest_layer(feature_line(0), 1)


if __name__ == "__main__":
    unittest.main()

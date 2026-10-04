import unittest

from rk65_layer0_prolonged_sound import build_write


class ProlongedSoundPatchTests(unittest.TestCase):
    def test_changes_only_the_key_right_of_l(self):
        response = bytearray(512)
        response[:8] = bytes([6, 0x83, 0, 0, 1, 0, 0xF8, 1])
        response[8 + 63 * 4 : 8 + 64 * 4] = bytes([0, 0, 0, 0x33])
        response[8 + 57 * 4 : 8 + 58 * 4] = bytes([0, 0, 0, 0x0F])
        response[8 + 35 * 4 : 8 + 36 * 4] = bytes([0x0D, 0, 0, 0])
        request = build_write({"format": "rk65-beiying-matrix-backup-v1", "responseBytes": list(response)})
        self.assertEqual(len(request), 519)
        self.assertEqual(request[:7], bytes([3, 0, 0, 1, 0, 0xF8, 1]))
        self.assertEqual(request[7 + 63 * 4 : 11 + 63 * 4], bytes([0, 0, 0, 0x2D]))
        self.assertEqual(request[7 + 57 * 4 : 11 + 57 * 4], bytes([0, 0, 0, 0x0F]))
        self.assertEqual(request[7 + 35 * 4 : 11 + 35 * 4], bytes([0x0D, 0, 0, 0]))

    def test_rejects_unexpected_source_mapping(self):
        response = bytearray(512)
        response[:8] = bytes([6, 0x83, 0, 0, 1, 0, 0xF8, 1])
        with self.assertRaises(ValueError):
            build_write({"format": "rk65-beiying-matrix-backup-v1", "responseBytes": list(response)})


if __name__ == "__main__":
    unittest.main()

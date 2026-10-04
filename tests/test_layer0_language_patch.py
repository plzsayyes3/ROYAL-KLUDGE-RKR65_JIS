import unittest

from rk65_layer0_language_patch import (
    LANG1,
    LANG2,
    build_layer0_write,
    parse_backup,
)


class Layer0LanguagePatchTests(unittest.TestCase):
    def make_response(self):
        response = bytearray(512)
        response[:8] = bytes([6, 0x83, 0, 0, 1, 0, 0xF8, 1])
        response[8 + 23 * 4 : 8 + 24 * 4] = bytes([0, 0, 0, 0x8B])
        response[8 + 41 * 4 : 8 + 42 * 4] = bytes([0, 0, 0, 0x8A])
        response[8 + 35 * 4 : 8 + 36 * 4] = bytes([0x0D, 0, 0, 0])
        return response

    def test_patches_space_neighbors_and_preserves_everything_else(self):
        response = self.make_response()
        request = build_layer0_write(response)
        self.assertEqual(len(request), 519)
        self.assertEqual(request[:7], bytes([3, 0, 0, 1, 0, 0xF8, 1]))
        self.assertEqual(request[7 + 23 * 4 : 11 + 23 * 4], LANG2)
        self.assertEqual(request[7 + 41 * 4 : 11 + 41 * 4], LANG1)
        self.assertEqual(request[7 + 35 * 4 : 11 + 35 * 4], bytes([0x0D, 0, 0, 0]))
        changed = set(range(23 * 4, 24 * 4)) | set(range(41 * 4, 42 * 4))
        for index, (old_index, new_index) in enumerate(zip(response[8:], request[7:])):
            if index not in changed:
                self.assertEqual(old_index, new_index)

    def test_rejects_unexpected_existing_neighbor_values(self):
        response = self.make_response()
        response[8 + 23 * 4 + 3] = 0
        with self.assertRaises(ValueError):
            build_layer0_write(response)

    def test_rejects_wrong_backup_header(self):
        response = self.make_response()
        response[1] = 0
        with self.assertRaises(ValueError):
            parse_backup({"responseBytes": list(response)})


if __name__ == "__main__":
    unittest.main()

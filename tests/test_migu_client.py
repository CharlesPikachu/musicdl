import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from musicdl.modules.sources import MiguMusicClient

class TestMiguMusicClient(unittest.TestCase):
    def test_initialization(self):
        client = MiguMusicClient()
        self.assertIsNotNone(client)
        self.assertEqual(client.source, 'MiguMusicClient')

    def test_parseplaylist_method_exists(self):
        client = MiguMusicClient()
        self.assertTrue(hasattr(client, 'parseplaylist'))
        self.assertTrue(callable(client.parseplaylist))

if __name__ == '__main__':
    unittest.main()
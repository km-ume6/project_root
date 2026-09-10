import unittest
from unittest.mock import patch

from backend.db_connector import get_connection


class DbConnectorTests(unittest.TestCase):
    def test_get_connection_raises_runtime_error_with_detail(self):
        with patch("backend.db_connector.pyodbc.connect", side_effect=Exception("boom")):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                get_connection()


if __name__ == "__main__":
    unittest.main()

"""Unit tests for __main__ module."""

import importlib
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMainModule:
    """Tests for __main__ module."""

    def test_main_is_called(self) -> None:
        """Test that main() is called when module is executed."""
        with patch("orfmi.cli.main") as mock_main:
            # Import must happen inside the test with patch active
            # because __main__.py calls main() on import
            module = importlib.import_module("orfmi.__main__")
            importlib.reload(module)
            mock_main.assert_called_once()

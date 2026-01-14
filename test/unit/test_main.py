"""Unit tests for __main__ module."""

import importlib
import sys
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMainModule:
    """Tests for __main__ module."""

    def test_main_is_called(self) -> None:
        """Test that main() is called when module is executed."""
        # Remove module from cache if already imported
        sys.modules.pop("orfmi.__main__", None)
        with patch("orfmi.cli.main") as mock_main:
            importlib.import_module("orfmi.__main__")
            mock_main.assert_called_once()

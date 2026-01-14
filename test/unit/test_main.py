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
            assert mock_main.call_count == 1

    def test_module_is_importable(self) -> None:
        """Test that __main__ module can be imported."""
        sys.modules.pop("orfmi.__main__", None)
        with patch("orfmi.cli.main"):
            module = importlib.import_module("orfmi.__main__")
            assert module is not None

"""Unit tests for __main__ module."""

import importlib
from unittest.mock import patch

import pytest

import orfmi.__main__


@pytest.mark.unit
class TestMainModule:
    """Tests for __main__ module."""

    def test_main_is_called(self) -> None:
        """Test that main() is called when module is executed."""
        with patch("orfmi.cli.main") as mock_main:
            importlib.reload(orfmi.__main__)
            mock_main.assert_called_once()

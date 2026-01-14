"""Unit tests for __main__ module."""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMainModule:
    """Tests for __main__ module."""

    def test_main_is_called(self) -> None:
        """Test that main() is called when module is executed."""
        with patch("ormi.cli.main") as mock_main:
            import importlib
            import ormi.__main__
            importlib.reload(ormi.__main__)
            mock_main.assert_called_once()

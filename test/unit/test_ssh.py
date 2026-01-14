"""Unit tests for SSH module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ormi.ssh import SshConfig, connect_ssh, run_setup_script, upload_file


@pytest.mark.unit
class TestSshConfig:
    """Tests for SshConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
        )
        assert config.timeout == 300
        assert config.retries == 30

    def test_all_values(self) -> None:
        """Test all values."""
        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            timeout=600,
            retries=60,
        )
        assert config.ip_address == "1.2.3.4"
        assert config.key_material == "private-key"
        assert config.username == "admin"
        assert config.timeout == 600
        assert config.retries == 60


@pytest.mark.unit
class TestConnectSsh:
    """Tests for connect_ssh function."""

    @patch("ormi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("ormi.ssh.paramiko.SSHClient")
    def test_successful_connection(
        self, mock_client_class: MagicMock, mock_key_class: MagicMock
    ) -> None:
        """Test successful SSH connection."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_key = MagicMock()
        mock_key_class.return_value = mock_key

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
        )
        result = connect_ssh(config)
        assert result == mock_client
        mock_client.connect.assert_called_once()

    @patch("ormi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("ormi.ssh.paramiko.SSHClient")
    @patch("time.sleep")
    def test_retries_on_failure(
        self,
        mock_sleep: MagicMock,
        mock_client_class: MagicMock,
        mock_key_class: MagicMock,
    ) -> None:
        """Test that connection is retried on failure."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_key = MagicMock()
        mock_key_class.return_value = mock_key
        mock_client.connect.side_effect = [TimeoutError, None]

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            retries=2,
        )
        result = connect_ssh(config)
        assert result == mock_client
        assert mock_client.connect.call_count == 2

    @patch("ormi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("ormi.ssh.paramiko.SSHClient")
    @patch("time.sleep")
    def test_raises_after_max_retries(
        self,
        mock_sleep: MagicMock,
        mock_client_class: MagicMock,
        mock_key_class: MagicMock,
    ) -> None:
        """Test that RuntimeError is raised after max retries."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_key = MagicMock()
        mock_key_class.return_value = mock_key
        mock_client.connect.side_effect = TimeoutError

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            retries=2,
        )
        with pytest.raises(RuntimeError, match="Failed to connect"):
            connect_ssh(config)


@pytest.mark.unit
class TestUploadFile:
    """Tests for upload_file function."""

    def test_uploads_file(self, tmp_path: Path) -> None:
        """Test file upload."""
        sftp = MagicMock()
        local_file = tmp_path / "test.txt"
        local_file.write_text("test content")
        upload_file(sftp, local_file, "/tmp/test.txt")
        sftp.put.assert_called_once_with(str(local_file), "/tmp/test.txt")


@pytest.mark.unit
class TestRunSetupScript:
    """Tests for run_setup_script function."""

    @patch("ormi.ssh.connect_ssh")
    @patch("ormi.ssh.run_ssh_command")
    def test_runs_script(
        self, mock_run_cmd: MagicMock, mock_connect: MagicMock, tmp_path: Path
    ) -> None:
        """Test running setup script."""
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp

        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
        )
        run_setup_script(config, setup_script)

        mock_sftp.put.assert_called_once()
        mock_sftp.chmod.assert_called_once()
        mock_run_cmd.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("ormi.ssh.connect_ssh")
    @patch("ormi.ssh.run_ssh_command")
    def test_uploads_extra_files(
        self, mock_run_cmd: MagicMock, mock_connect: MagicMock, tmp_path: Path
    ) -> None:
        """Test uploading extra files."""
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp

        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        extra_file = tmp_path / "extra.txt"
        extra_file.write_text("extra content")

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
        )
        run_setup_script(config, setup_script, [extra_file])

        assert mock_sftp.put.call_count == 2

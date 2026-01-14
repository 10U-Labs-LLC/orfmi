"""Unit tests for SSH module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from orfmi.ssh import SshConfig, connect_ssh, run_setup_script, run_ssh_command, upload_file


@pytest.mark.unit
class TestSshConfigDefaults:
    """Tests for SshConfig default values."""

    def test_timeout_default(self, default_ssh_config: SshConfig) -> None:
        """Test timeout default value."""
        assert default_ssh_config.timeout == 300

    def test_retries_default(self, default_ssh_config: SshConfig) -> None:
        """Test retries default value."""
        assert default_ssh_config.retries == 30


@pytest.mark.unit
class TestSshConfigAllValues:
    """Tests for SshConfig with all values set."""

    def test_ip_address(self, full_ssh_config: SshConfig) -> None:
        """Test ip_address is set correctly."""
        assert full_ssh_config.ip_address == "1.2.3.4"

    def test_key_material(self, full_ssh_config: SshConfig) -> None:
        """Test key_material is set correctly."""
        assert full_ssh_config.key_material == "private-key"

    def test_username(self, full_ssh_config: SshConfig) -> None:
        """Test username is set correctly."""
        assert full_ssh_config.username == "admin"

    def test_timeout(self, full_ssh_config: SshConfig) -> None:
        """Test timeout is set correctly."""
        assert full_ssh_config.timeout == 600

    def test_retries(self, full_ssh_config: SshConfig) -> None:
        """Test retries is set correctly."""
        assert full_ssh_config.retries == 60


@pytest.mark.unit
class TestConnectSsh:
    """Tests for connect_ssh function."""

    @patch("orfmi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("orfmi.ssh.paramiko.SSHClient")
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

    @patch("orfmi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("orfmi.ssh.paramiko.SSHClient")
    def test_successful_connection_calls_connect(
        self, mock_client_class: MagicMock, mock_key_class: MagicMock
    ) -> None:
        """Test successful SSH connection calls connect."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_key = MagicMock()
        mock_key_class.return_value = mock_key

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
        )
        connect_ssh(config)
        assert mock_client.connect.call_count == 1

    def test_retries_on_failure_returns_client(
        self, retry_ssh_mocks: dict[str, Any]
    ) -> None:
        """Test that connection is retried on failure and returns client."""
        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            retries=2,
        )
        result = connect_ssh(config)
        assert result == retry_ssh_mocks["mock_client"]

    def test_retries_on_failure_call_count(
        self, retry_ssh_mocks: dict[str, Any]
    ) -> None:
        """Test that connect is called twice on retry."""
        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            retries=2,
        )
        connect_ssh(config)
        assert retry_ssh_mocks["mock_client"].connect.call_count == 2

    @patch("orfmi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("orfmi.ssh.paramiko.SSHClient")
    @patch("time.sleep")
    def test_raises_after_max_retries(
        self,
        _mock_sleep: MagicMock,
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

    @patch("orfmi.ssh.paramiko.Ed25519Key.from_private_key")
    @patch("orfmi.ssh.paramiko.SSHClient")
    def test_raises_when_retries_is_zero(
        self,
        mock_client_class: MagicMock,
        mock_key_class: MagicMock,
    ) -> None:
        """Test that RuntimeError is raised when retries is 0."""
        mock_client_class.return_value = MagicMock()
        mock_key_class.return_value = MagicMock()

        config = SshConfig(
            ip_address="1.2.3.4",
            key_material="private-key",
            username="admin",
            retries=0,
        )
        with pytest.raises(RuntimeError, match="retries was 0"):
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
        assert sftp.put.call_args[0] == (str(local_file), "/tmp/test.txt")

    def test_uploads_file_calls_put(self, tmp_path: Path) -> None:
        """Test that upload_file calls sftp.put."""
        sftp = MagicMock()
        local_file = tmp_path / "file.txt"
        local_file.write_text("content")
        upload_file(sftp, local_file, "/remote/file.txt")
        assert sftp.put.called


@pytest.mark.unit
class TestRunSetupScript:
    """Tests for run_setup_script function."""

    def test_runs_script_calls_put(
        self, run_setup_script_mocks: dict[str, Any]
    ) -> None:
        """Test running setup script calls sftp.put."""
        assert run_setup_script_mocks["mock_sftp"].put.call_count == 1

    def test_runs_script_calls_chmod(
        self, run_setup_script_mocks: dict[str, Any]
    ) -> None:
        """Test running setup script calls sftp.chmod."""
        assert run_setup_script_mocks["mock_sftp"].chmod.call_count == 1

    def test_runs_script_calls_run_ssh_command(
        self, run_setup_script_mocks: dict[str, Any]
    ) -> None:
        """Test running setup script calls run_ssh_command."""
        assert run_setup_script_mocks["mock_run_cmd"].call_count == 1

    def test_runs_script_calls_close(
        self, run_setup_script_mocks: dict[str, Any]
    ) -> None:
        """Test running setup script closes connection."""
        assert run_setup_script_mocks["mock_client"].close.call_count == 1

    @patch("orfmi.ssh.connect_ssh")
    @patch("orfmi.ssh.run_ssh_command")
    def test_uploads_extra_files(
        self, _mock_run_cmd: MagicMock, mock_connect: MagicMock, tmp_path: Path
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


@pytest.mark.unit
class TestRunSshCommand:
    """Tests for run_ssh_command function."""

    @patch("time.sleep")
    @patch("sys.stdout")
    def test_runs_command_success(
        self,
        _mock_stdout: MagicMock,
        _mock_sleep: MagicMock,
        ssh_command_channel: dict[str, Any],
    ) -> None:
        """Test successful command execution."""
        client = ssh_command_channel["client"]
        channel = ssh_command_channel["channel"]
        channel.exit_status_ready.side_effect = [False, True]
        channel.recv_ready.side_effect = [True, False]
        channel.recv.return_value = b"output"
        channel.recv_exit_status.return_value = 0
        run_ssh_command(client, "echo test")
        assert client.exec_command.call_count == 1

    @patch("time.sleep")
    @patch("sys.stdout")
    def test_raises_on_nonzero_exit(
        self,
        _mock_stdout: MagicMock,
        _mock_sleep: MagicMock,
        ssh_command_channel: dict[str, Any],
    ) -> None:
        """Test that RuntimeError is raised on nonzero exit code."""
        client = ssh_command_channel["client"]
        channel = ssh_command_channel["channel"]
        channel.exit_status_ready.return_value = True
        channel.recv_ready.return_value = False
        channel.recv_exit_status.return_value = 1
        with pytest.raises(RuntimeError, match="exit code 1"):
            run_ssh_command(client, "false")

    @patch("time.sleep")
    @patch("sys.stdout")
    def test_streams_output(
        self,
        mock_stdout: MagicMock,
        _mock_sleep: MagicMock,
        ssh_command_channel: dict[str, Any],
    ) -> None:
        """Test that output is streamed to stdout."""
        client = ssh_command_channel["client"]
        channel = ssh_command_channel["channel"]
        channel.exit_status_ready.side_effect = [False, True]
        channel.recv_ready.side_effect = [True, False]
        channel.recv.return_value = b"test output"
        channel.recv_exit_status.return_value = 0
        run_ssh_command(client, "echo test")
        assert mock_stdout.write.called

    @patch("time.sleep")
    @patch("sys.stdout")
    def test_drains_remaining_output(
        self,
        mock_stdout: MagicMock,
        _mock_sleep: MagicMock,
        ssh_command_channel: dict[str, Any],
    ) -> None:
        """Test that remaining output is drained after exit status ready."""
        client = ssh_command_channel["client"]
        channel = ssh_command_channel["channel"]
        channel.exit_status_ready.return_value = True
        channel.recv_ready.side_effect = [True, False]
        channel.recv.return_value = b"remaining output"
        channel.recv_exit_status.return_value = 0
        run_ssh_command(client, "echo test")
        assert mock_stdout.write.call_count >= 1

"""Unit test configuration."""

from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from orfmi.ec2 import create_ami
from orfmi.ssh import SshConfig, run_setup_script


@pytest.fixture
def run_setup_script_mocks(
    tmp_path: Path,
) -> Generator[dict[str, Any], None, None]:
    """Create mocks for run_setup_script tests."""
    with (
        patch("orfmi.ssh.connect_ssh") as mock_connect,
        patch("orfmi.ssh.run_ssh_command") as mock_run_cmd,
    ):
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

        yield {
            "mock_connect": mock_connect,
            "mock_run_cmd": mock_run_cmd,
            "mock_client": mock_client,
            "mock_sftp": mock_sftp,
            "setup_script": setup_script,
            "config": config,
        }


@pytest.fixture
def retry_ssh_mocks() -> Generator[dict[str, Any], None, None]:
    """Create mocks for SSH retry tests."""
    with (
        patch("orfmi.ssh.paramiko.Ed25519Key.from_private_key") as mock_key_class,
        patch("orfmi.ssh.paramiko.SSHClient") as mock_client_class,
        patch("time.sleep"),
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_key = MagicMock()
        mock_key_class.return_value = mock_key
        mock_client.connect.side_effect = [TimeoutError, None]

        yield {
            "mock_client_class": mock_client_class,
            "mock_key_class": mock_key_class,
            "mock_client": mock_client,
            "mock_key": mock_key,
        }


@pytest.fixture
def create_ami_with_tags_mocks() -> dict[str, Any]:
    """Create mocks for create_ami with tags tests."""
    ec2 = MagicMock()
    ec2.create_image.return_value = {"ImageId": "ami-12345"}
    waiter = MagicMock()
    ec2.get_waiter.return_value = waiter
    ec2.describe_images.return_value = {
        "Images": [{
            "BlockDeviceMappings": [
                {"Ebs": {"SnapshotId": "snap-12345"}}
            ]
        }]
    }
    create_ami(ec2, "i-12345", "test-ami", "Test AMI", {"Name": "test"})
    return {"ec2": ec2, "waiter": waiter}


@pytest.fixture
def ssh_command_channel() -> dict[str, Any]:
    """Create channel mock for SSH command tests."""
    client = MagicMock()
    channel = MagicMock()
    stdout = MagicMock()
    stdout.channel = channel
    client.exec_command.return_value = (None, stdout, None)
    return {"client": client, "channel": channel, "stdout": stdout}


@pytest.fixture
def fleet_ec2_mock() -> MagicMock:
    """Create EC2 mock for fleet instance tests."""
    ec2 = MagicMock()
    ec2.describe_launch_templates.return_value = {
        "LaunchTemplates": [{"LaunchTemplateId": "lt-12345"}]
    }
    ec2.create_fleet.return_value = {
        "Instances": [{"InstanceIds": ["i-12345"]}]
    }
    return ec2

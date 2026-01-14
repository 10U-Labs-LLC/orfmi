"""SSH operations for running setup scripts on EC2 instances."""

import logging
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class SshConfig:
    """Configuration for SSH connection."""

    ip_address: str
    key_material: str
    username: str
    timeout: int = 300
    retries: int = 30


def run_ssh_command(client: paramiko.SSHClient, cmd: str, timeout: int = 600) -> None:
    """Run a command over SSH and stream output to stdout."""
    _, stdout, _ = client.exec_command(cmd, timeout=timeout, get_pty=True)
    channel = stdout.channel
    while not channel.exit_status_ready():
        if channel.recv_ready():
            sys.stdout.write(channel.recv(4096).decode())
            sys.stdout.flush()
        time.sleep(0.1)
    while channel.recv_ready():
        sys.stdout.write(channel.recv(4096).decode())
        sys.stdout.flush()
    exit_code = channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(f"Command failed with exit code {exit_code}")


def connect_ssh(config: SshConfig) -> paramiko.SSHClient:
    """Establish an SSH connection with retry logic.

    Args:
        config: SSH configuration.

    Returns:
        Connected SSHClient.

    Raises:
        RuntimeError: If connection fails after all retries or retries is 0.
    """
    key = paramiko.Ed25519Key.from_private_key(StringIO(config.key_material))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(config.retries):
        try:
            client.connect(
                config.ip_address,
                username=config.username,
                pkey=key,
                timeout=10,
            )
            return client
        except (
            paramiko.ssh_exception.NoValidConnectionsError,
            TimeoutError,
            OSError,
        ) as exc:
            if attempt == config.retries - 1:
                raise RuntimeError(
                    f"Failed to connect to {config.ip_address} "
                    f"after {config.retries} attempts"
                ) from exc
            time.sleep(10)

    raise RuntimeError(f"Failed to connect to {config.ip_address}: retries was 0")


def upload_file(sftp: paramiko.SFTPClient, local_path: Path, remote_path: str) -> None:
    """Upload a file via SFTP."""
    sftp.put(str(local_path), remote_path)


def run_setup_script(
    config: SshConfig,
    setup_script: Path,
    extra_files: list[Path] | None = None,
) -> None:
    """Upload and run the setup script on the instance via SSH.

    Args:
        config: SSH configuration.
        setup_script: Path to the setup script to run.
        extra_files: Optional list of additional files to upload.
    """
    client = connect_ssh(config)

    try:
        sftp = client.open_sftp()

        remote_script = f"/tmp/{setup_script.name}"
        sftp.put(str(setup_script), remote_script)
        sftp.chmod(remote_script, 0o755)

        if extra_files:
            for extra_file in extra_files:
                if extra_file.exists():
                    sftp.put(str(extra_file), f"/tmp/{extra_file.name}")

        sftp.close()

        logger.info("Running setup script: %s", setup_script.name)
        full_cmd = f"sudo bash -c '{remote_script}'"
        run_ssh_command(client, full_cmd, timeout=config.timeout)
    finally:
        client.close()

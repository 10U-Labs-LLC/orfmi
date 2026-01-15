"""Integration test configuration."""

from pathlib import Path
from test.conftest import run_main_with_args
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture
def full_config_result(tmp_path: Path) -> tuple[int, Any]:
    """Run CLI with full config and return exit code and parsed config."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: my-custom-ami
region: us-west-2
source_ami: ubuntu-22.04-*
subnet_ids:
  - subnet-aaa
  - subnet-bbb
instance_types:
  - t3.micro
  - t3.small
security_group_id: sg-12345
ami_description: My custom AMI for testing
iam_instance_profile: my-profile
ssh_username: ubuntu
ssh_timeout: 600
ssh_retries: 60
platform: linux
tags:
  Name: test
  Environment: dev
""")
    setup_file = tmp_path / "setup.sh"
    setup_file.write_text("#!/bin/bash\necho 'Hello'")

    with patch("orfmi.cli.AmiBuilder") as mock_builder:
        mock_builder.return_value.build.return_value = "ami-12345"
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        ])
        config = mock_builder.call_args[0][0]
        return exit_code, config

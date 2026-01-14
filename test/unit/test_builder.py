"""Unit tests for builder module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orfmi.builder import AmiBuilder, BuildContext, BuildState
from orfmi.config import AmiConfig


@pytest.mark.unit
class TestBuildState:
    """Tests for BuildState dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        state = BuildState()
        assert state.instance_id is None
        assert state.sg_id is None
        assert state.key_material is None
        assert state.result is None

    def test_mutable(self) -> None:
        """Test that state is mutable."""
        state = BuildState()
        state.instance_id = "i-12345"
        assert state.instance_id == "i-12345"


@pytest.mark.unit
class TestBuildContext:
    """Tests for BuildContext dataclass."""

    def test_all_values(self, tmp_path: Path) -> None:
        """Test all values."""
        ec2 = MagicMock()
        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "setup.sh"
        ctx = BuildContext(
            ec2=ec2,
            config=config,
            setup_script=setup_script,
            unique_id="abc12345",
            extra_files=[tmp_path / "extra.txt"],
        )
        assert ctx.ec2 == ec2
        assert ctx.config == config
        assert ctx.setup_script == setup_script
        assert ctx.unique_id == "abc12345"
        assert len(ctx.extra_files) == 1


@pytest.mark.unit
class TestAmiBuilder:
    """Tests for AmiBuilder class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test AmiBuilder initialization."""
        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "setup.sh"
        builder = AmiBuilder(config, setup_script)
        assert builder.config == config
        assert builder.setup_script == setup_script
        assert builder.extra_files == []

    def test_init_with_extra_files(self, tmp_path: Path) -> None:
        """Test AmiBuilder initialization with extra files."""
        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "setup.sh"
        extra_files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]
        builder = AmiBuilder(config, setup_script, extra_files)
        assert builder.extra_files == extra_files

    @patch("orfmi.builder.create_ec2_client")
    @patch("orfmi.builder.generate_unique_id")
    @patch("orfmi.builder.get_vpc_from_subnet")
    @patch("orfmi.builder.create_key_pair")
    @patch("orfmi.builder.create_security_group")
    @patch("orfmi.builder.lookup_source_ami")
    @patch("orfmi.builder.create_launch_template")
    @patch("orfmi.builder.create_fleet_instance")
    @patch("orfmi.builder.wait_for_instance")
    @patch("orfmi.builder.run_setup_script")
    @patch("orfmi.builder.create_ami")
    @patch("orfmi.builder.terminate_instance")
    @patch("orfmi.builder.delete_launch_template")
    @patch("orfmi.builder.delete_key_pair")
    @patch("orfmi.builder.delete_security_group")
    def test_build_success(
        self,
        mock_delete_sg: MagicMock,
        mock_delete_key: MagicMock,
        mock_delete_template: MagicMock,
        mock_terminate: MagicMock,
        mock_create_ami: MagicMock,
        mock_run_script: MagicMock,
        mock_wait: MagicMock,
        mock_create_fleet: MagicMock,
        mock_create_template: MagicMock,
        mock_lookup: MagicMock,
        mock_create_sg: MagicMock,
        mock_create_key: MagicMock,
        mock_get_vpc: MagicMock,
        mock_unique_id: MagicMock,
        mock_ec2_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful build."""
        mock_ec2 = MagicMock()
        mock_ec2_client.return_value = mock_ec2
        mock_unique_id.return_value = "abc12345"
        mock_get_vpc.return_value = "vpc-12345"
        mock_create_key.return_value = "private-key"
        mock_create_sg.return_value = "sg-12345"
        mock_lookup.return_value = "ami-source"
        mock_create_fleet.return_value = "i-12345"
        mock_wait.return_value = "1.2.3.4"
        mock_create_ami.return_value = "ami-result"

        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")

        builder = AmiBuilder(config, setup_script)
        result = builder.build()

        assert result == "ami-result"
        mock_create_key.assert_called_once()
        mock_create_sg.assert_called_once()
        mock_create_template.assert_called_once()
        mock_create_fleet.assert_called_once()
        mock_run_script.assert_called_once()
        mock_create_ami.assert_called_once()
        mock_terminate.assert_called_once()
        mock_delete_sg.assert_called_once()

    @patch("orfmi.builder.create_ec2_client")
    @patch("orfmi.builder.generate_unique_id")
    @patch("orfmi.builder.get_vpc_from_subnet")
    @patch("orfmi.builder.create_key_pair")
    @patch("orfmi.builder.create_security_group")
    @patch("orfmi.builder.lookup_source_ami")
    @patch("orfmi.builder.create_launch_template")
    @patch("orfmi.builder.create_fleet_instance")
    @patch("orfmi.builder.terminate_instance")
    @patch("orfmi.builder.delete_launch_template")
    @patch("orfmi.builder.delete_key_pair")
    @patch("orfmi.builder.delete_security_group")
    def test_cleanup_on_failure(
        self,
        mock_delete_sg: MagicMock,
        mock_delete_key: MagicMock,
        mock_delete_template: MagicMock,
        mock_terminate: MagicMock,
        mock_create_fleet: MagicMock,
        mock_create_template: MagicMock,
        mock_lookup: MagicMock,
        mock_create_sg: MagicMock,
        mock_create_key: MagicMock,
        mock_get_vpc: MagicMock,
        mock_unique_id: MagicMock,
        mock_ec2_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test cleanup happens on build failure."""
        mock_ec2 = MagicMock()
        mock_ec2_client.return_value = mock_ec2
        mock_unique_id.return_value = "abc12345"
        mock_get_vpc.return_value = "vpc-12345"
        mock_create_key.return_value = "private-key"
        mock_create_sg.return_value = "sg-12345"
        mock_lookup.return_value = "ami-source"
        mock_create_fleet.side_effect = RuntimeError("Fleet creation failed")

        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")

        builder = AmiBuilder(config, setup_script)

        with pytest.raises(RuntimeError):
            builder.build()

        mock_delete_key.assert_called_once()
        mock_delete_template.assert_called_once()

    @patch("orfmi.builder.create_ec2_client")
    @patch("orfmi.builder.generate_unique_id")
    @patch("orfmi.builder.get_vpc_from_subnet")
    @patch("orfmi.builder.create_key_pair")
    @patch("orfmi.builder.create_security_group")
    @patch("orfmi.builder.lookup_source_ami")
    @patch("orfmi.builder.create_launch_template")
    @patch("orfmi.builder.create_fleet_instance")
    @patch("orfmi.builder.wait_for_instance")
    @patch("orfmi.builder.create_ami")
    @patch("orfmi.builder.terminate_instance")
    @patch("orfmi.builder.delete_launch_template")
    @patch("orfmi.builder.delete_key_pair")
    @patch("orfmi.builder.delete_security_group")
    def test_skips_script_if_not_exists(
        self,
        mock_delete_sg: MagicMock,
        mock_delete_key: MagicMock,
        mock_delete_template: MagicMock,
        mock_terminate: MagicMock,
        mock_create_ami: MagicMock,
        mock_wait: MagicMock,
        mock_create_fleet: MagicMock,
        mock_create_template: MagicMock,
        mock_lookup: MagicMock,
        mock_create_sg: MagicMock,
        mock_create_key: MagicMock,
        mock_get_vpc: MagicMock,
        mock_unique_id: MagicMock,
        mock_ec2_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that setup script is skipped if it doesn't exist."""
        mock_ec2 = MagicMock()
        mock_ec2_client.return_value = mock_ec2
        mock_unique_id.return_value = "abc12345"
        mock_get_vpc.return_value = "vpc-12345"
        mock_create_key.return_value = "private-key"
        mock_create_sg.return_value = "sg-12345"
        mock_lookup.return_value = "ami-source"
        mock_create_fleet.return_value = "i-12345"
        mock_wait.return_value = "1.2.3.4"
        mock_create_ami.return_value = "ami-result"

        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        setup_script = tmp_path / "nonexistent.sh"

        builder = AmiBuilder(config, setup_script)
        result = builder.build()

        assert result == "ami-result"

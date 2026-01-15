"""Unit tests for builder module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from botocore.exceptions import ClientError

from orfmi.builder import AmiBuilder, BuildContext, BuildState
from orfmi.config import AmiConfig, AmiIdentity, InstanceSettings
from orfmi.ec2 import CapacityError, InstanceTerminatedError


def make_test_config() -> AmiConfig:
    """Create a test AmiConfig."""
    ami = AmiIdentity(name="test-ami")
    instance = InstanceSettings(
        subnet_ids=["subnet-1"],
        instance_types=["t3.micro"],
        security_group_id="sg-12345",
    )
    return AmiConfig(
        ami=ami,
        region="us-east-1",
        source_ami="ami-12345",
        instance=instance,
    )


@pytest.mark.unit
class TestBuildState:
    """Tests for BuildState dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        state = BuildState()
        assert state.instance_id is None

    def test_key_material_default(self) -> None:
        """Test key_material default value."""
        state = BuildState()
        assert state.key_material is None

    def test_result_default(self) -> None:
        """Test result default value."""
        state = BuildState()
        assert state.result is None

    def test_mutable(self) -> None:
        """Test that state is mutable."""
        state = BuildState()
        state.instance_id = "i-12345"
        assert state.instance_id == "i-12345"


@pytest.mark.unit
class TestBuildContext:
    """Tests for BuildContext dataclass."""

    def test_ec2_attribute(self, tmp_path: Path) -> None:
        """Test ec2 attribute is set correctly."""
        ec2 = MagicMock()
        ctx = BuildContext(
            ec2=ec2,
            config=make_test_config(),
            setup_script=tmp_path / "setup.sh",
            unique_id="abc12345",
        )
        assert ctx.ec2 == ec2

    def test_config_attribute(self, tmp_path: Path) -> None:
        """Test config attribute is set correctly."""
        config = make_test_config()
        ctx = BuildContext(
            ec2=MagicMock(),
            config=config,
            setup_script=tmp_path / "setup.sh",
            unique_id="abc12345",
        )
        assert ctx.config == config

    def test_setup_script_attribute(self, tmp_path: Path) -> None:
        """Test setup_script attribute is set correctly."""
        setup_script = tmp_path / "setup.sh"
        ctx = BuildContext(
            ec2=MagicMock(),
            config=make_test_config(),
            setup_script=setup_script,
            unique_id="abc12345",
        )
        assert ctx.setup_script == setup_script

    def test_unique_id_attribute(self, tmp_path: Path) -> None:
        """Test unique_id attribute is set correctly."""
        ctx = BuildContext(
            ec2=MagicMock(),
            config=make_test_config(),
            setup_script=tmp_path / "setup.sh",
            unique_id="abc12345",
        )
        assert ctx.unique_id == "abc12345"

    def test_resource_name_without_suffix(self, tmp_path: Path) -> None:
        """Test resource_name without suffix."""
        ctx = BuildContext(
            ec2=MagicMock(),
            config=make_test_config(),
            setup_script=tmp_path / "setup.sh",
            unique_id="abc12345",
        )
        assert ctx.resource_name() == "orfmi-abc12345"

    def test_resource_name_with_suffix(self, tmp_path: Path) -> None:
        """Test resource_name with suffix."""
        ctx = BuildContext(
            ec2=MagicMock(),
            config=make_test_config(),
            setup_script=tmp_path / "setup.sh",
            unique_id="abc12345",
        )
        assert ctx.resource_name("key") == "orfmi-abc12345-key"


@pytest.mark.unit
class TestAmiBuilder:
    """Tests for AmiBuilder class."""

    def test_init_config(self, tmp_path: Path) -> None:
        """Test AmiBuilder config initialization."""
        config = make_test_config()
        builder = AmiBuilder(config, tmp_path / "setup.sh")
        assert builder.config == config

    def test_init_setup_script(self, tmp_path: Path) -> None:
        """Test AmiBuilder setup_script initialization."""
        setup_script = tmp_path / "setup.sh"
        builder = AmiBuilder(make_test_config(), setup_script)
        assert builder.setup_script == setup_script

    def test_validate_returns_true(self, tmp_path: Path) -> None:
        """Test validate returns True for valid config."""
        builder = AmiBuilder(make_test_config(), tmp_path / "setup.sh")
        assert builder.validate() is True

    def test_build_returns_ami_id(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test successful build returns AMI ID."""
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        result = builder.build()
        assert result == builder_mocks["create_ami"].return_value

    def test_build_calls_create_key(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test build calls create_key_pair."""
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["create_key"].call_count == 1

    def test_build_calls_create_ami(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test build calls create_ami."""
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["create_ami"].call_count == 1

    def test_build_calls_terminate(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test build calls terminate_instance."""
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["terminate"].call_count == 1

    def test_cleanup_on_failure_deletes_key(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test cleanup deletes key pair on failure."""
        builder_mocks["create_fleet"].side_effect = RuntimeError("Fleet failed")
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        try:
            builder.build()
        except RuntimeError:
            pass
        assert builder_mocks["delete_key"].call_count == 1

    def test_cleanup_on_failure_deletes_template(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test cleanup deletes launch template on failure."""
        builder_mocks["create_fleet"].side_effect = RuntimeError("Fleet failed")
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        try:
            builder.build()
        except RuntimeError:
            pass
        assert builder_mocks["delete_template"].call_count == 1

    def test_skips_script_if_not_exists(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that setup script is skipped if it doesn't exist."""
        setup_script = tmp_path / "nonexistent.sh"
        builder = AmiBuilder(make_test_config(), setup_script)
        result = builder.build()
        assert result == builder_mocks["create_ami"].return_value

    def test_raises_when_no_ami_result(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that RuntimeError is raised when no AMI ID is returned."""
        builder_mocks["create_ami"].return_value = None
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        with pytest.raises(RuntimeError, match="no AMI ID returned"):
            builder.build()

    def test_raises_when_no_instance_id(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that RuntimeError is raised when instance ID is not set."""
        builder_mocks["create_fleet"].return_value = None
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        with pytest.raises(RuntimeError, match="Instance ID not set"):
            builder.build()

    def test_raises_when_no_key_material(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that RuntimeError is raised when key material is not set."""
        builder_mocks["create_key"].return_value = None
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        with pytest.raises(RuntimeError, match="Key material not set"):
            builder.build()

    def test_calls_check_instance_state(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that check_instance_state is called."""
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["check_state"].call_count == 2


@pytest.mark.unit
class TestAmiBuilderRetry:
    """Tests for AmiBuilder retry logic."""

    def test_retries_on_capacity_error(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that build retries on CapacityError."""
        builder_mocks["create_fleet"].side_effect = [
            CapacityError("No capacity"),
            "i-12345",
        ]
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        result = builder.build()
        assert result == "ami-result"

    def test_retries_on_instance_terminated_error(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that build retries on InstanceTerminatedError."""
        builder_mocks["check_state"].side_effect = [
            InstanceTerminatedError("Spot interrupted"),
            None,
            None,
        ]
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        result = builder.build()
        assert result == "ami-result"

    def test_raises_after_max_retries(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that RuntimeError is raised after max retries."""
        builder_mocks["create_fleet"].side_effect = CapacityError("No capacity")
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        with pytest.raises(RuntimeError, match="Build failed after"):
            builder.build()

    def test_cleans_up_instance_on_retry(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that instance is cleaned up on retry."""
        builder_mocks["check_state"].side_effect = [
            InstanceTerminatedError("Spot interrupted"),
            None,
            None,
        ]
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["terminate"].call_count == 2

    def test_sleeps_between_retries(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that sleep is called between retries."""
        builder_mocks["create_fleet"].side_effect = [
            CapacityError("No capacity"),
            "i-12345",
        ]
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        builder.build()
        assert builder_mocks["time_sleep"].call_count == 1

    def test_handles_terminate_error_on_cleanup(
        self, tmp_path: Path, builder_mocks: dict[str, Any]
    ) -> None:
        """Test that terminate errors are handled during cleanup."""
        builder_mocks["check_state"].side_effect = [
            InstanceTerminatedError("Spot interrupted"),
            None,
            None,
        ]
        builder_mocks["terminate"].side_effect = [
            ClientError({"Error": {"Code": "InvalidInstanceID"}}, "TerminateInstances"),
            None,
        ]
        setup_script = tmp_path / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Hello'")
        builder = AmiBuilder(make_test_config(), setup_script)
        result = builder.build()
        assert result == "ami-result"

"""Unit tests for config module."""

from pathlib import Path

import pytest

from orfmi.config import AmiConfig, ConfigError, load_config


@pytest.mark.unit
class TestAmiConfigDefaults:
    """Tests for AmiConfig default values."""

    def test_ami_description_default(self, minimal_config: AmiConfig) -> None:
        """Test ami_description defaults to empty string."""
        assert minimal_config.ami.description == ""

    def test_iam_instance_profile_default(self, minimal_config: AmiConfig) -> None:
        """Test iam_instance_profile defaults to None."""
        assert minimal_config.instance.iam_instance_profile is None

    def test_tags_default(self, minimal_config: AmiConfig) -> None:
        """Test tags defaults to empty dict."""
        assert not minimal_config.tags

    def test_ssh_username_default(self, minimal_config: AmiConfig) -> None:
        """Test ssh_username defaults to admin."""
        assert minimal_config.ssh.username == "admin"

    def test_ssh_timeout_default(self, minimal_config: AmiConfig) -> None:
        """Test ssh_timeout defaults to 300."""
        assert minimal_config.ssh.timeout == 300

    def test_ssh_retries_default(self, minimal_config: AmiConfig) -> None:
        """Test ssh_retries defaults to 30."""
        assert minimal_config.ssh.retries == 30

    def test_platform_default(self, minimal_config: AmiConfig) -> None:
        """Test platform defaults to linux."""
        assert minimal_config.platform == "linux"


@pytest.mark.unit
class TestAmiConfigAllFields:
    """Tests for AmiConfig with all fields set."""

    def test_ami_name(self, full_config: AmiConfig) -> None:
        """Test ami_name is set correctly."""
        assert full_config.ami.name == "test-ami"

    def test_region(self, full_config: AmiConfig) -> None:
        """Test region is set correctly."""
        assert full_config.region == "us-west-2"

    def test_source_ami(self, full_config: AmiConfig) -> None:
        """Test source_ami is set correctly."""
        assert full_config.source_ami == "ami-67890"

    def test_subnet_ids(self, full_config: AmiConfig) -> None:
        """Test subnet_ids is set correctly."""
        assert full_config.instance.subnet_ids == ["subnet-1", "subnet-2"]

    def test_instance_types(self, full_config: AmiConfig) -> None:
        """Test instance_types is set correctly."""
        assert full_config.instance.instance_types == ["t3.micro", "t3.small"]

    def test_ami_description(self, full_config: AmiConfig) -> None:
        """Test ami_description is set correctly."""
        assert full_config.ami.description == "Test AMI"

    def test_iam_instance_profile(self, full_config: AmiConfig) -> None:
        """Test iam_instance_profile is set correctly."""
        assert full_config.instance.iam_instance_profile == "my-profile"

    def test_tags(self, full_config: AmiConfig) -> None:
        """Test tags is set correctly."""
        assert full_config.tags == {"Name": "test"}

    def test_ssh_username(self, full_config: AmiConfig) -> None:
        """Test ssh_username is set correctly."""
        assert full_config.ssh.username == "ec2-user"

    def test_ssh_timeout(self, full_config: AmiConfig) -> None:
        """Test ssh_timeout is set correctly."""
        assert full_config.ssh.timeout == 600

    def test_ssh_retries(self, full_config: AmiConfig) -> None:
        """Test ssh_retries is set correctly."""
        assert full_config.ssh.retries == 60

    def test_platform(self, full_config: AmiConfig) -> None:
        """Test platform is set correctly."""
        assert full_config.platform == "windows"


@pytest.mark.unit
class TestAmiConfigFrozen:
    """Tests for AmiConfig immutability."""

    def test_frozen(self, minimal_config: AmiConfig) -> None:
        """Test that config is immutable."""
        with pytest.raises(AttributeError):
            setattr(minimal_config, "region", "us-west-2")


@pytest.mark.unit
class TestLoadConfigMinimal:
    """Tests for load_config with minimal config."""

    def test_ami_name(self, loaded_minimal_config: AmiConfig) -> None:
        """Test ami_name is loaded correctly."""
        assert loaded_minimal_config.ami.name == "test-ami"

    def test_region(self, loaded_minimal_config: AmiConfig) -> None:
        """Test region is loaded correctly."""
        assert loaded_minimal_config.region == "us-east-1"

    def test_source_ami(self, loaded_minimal_config: AmiConfig) -> None:
        """Test source_ami is loaded correctly."""
        assert loaded_minimal_config.source_ami == "debian-12-*"

    def test_subnet_ids(self, loaded_minimal_config: AmiConfig) -> None:
        """Test subnet_ids is loaded correctly."""
        assert loaded_minimal_config.instance.subnet_ids == ["subnet-12345"]

    def test_instance_types(self, loaded_minimal_config: AmiConfig) -> None:
        """Test instance_types is loaded correctly."""
        assert loaded_minimal_config.instance.instance_types == ["t3.micro"]


@pytest.mark.unit
class TestLoadConfigFull:
    """Tests for load_config with full config."""

    def test_ami_name(self, loaded_full_config: AmiConfig) -> None:
        """Test ami_name is loaded correctly."""
        assert loaded_full_config.ami.name == "my-ami"

    def test_ami_description(self, loaded_full_config: AmiConfig) -> None:
        """Test ami_description is loaded correctly."""
        assert loaded_full_config.ami.description == "My custom AMI"

    def test_iam_instance_profile(self, loaded_full_config: AmiConfig) -> None:
        """Test iam_instance_profile is loaded correctly."""
        assert loaded_full_config.instance.iam_instance_profile == "my-profile"

    def test_ssh_username(self, loaded_full_config: AmiConfig) -> None:
        """Test ssh_username is loaded correctly."""
        assert loaded_full_config.ssh.username == "ubuntu"

    def test_ssh_timeout(self, loaded_full_config: AmiConfig) -> None:
        """Test ssh_timeout is loaded correctly."""
        assert loaded_full_config.ssh.timeout == 600

    def test_ssh_retries(self, loaded_full_config: AmiConfig) -> None:
        """Test ssh_retries is loaded correctly."""
        assert loaded_full_config.ssh.retries == 60

    def test_platform(self, loaded_full_config: AmiConfig) -> None:
        """Test platform is loaded correctly."""
        assert loaded_full_config.platform == "linux"

    def test_tags(self, loaded_full_config: AmiConfig) -> None:
        """Test tags are loaded correctly."""
        assert loaded_full_config.tags == {"Name": "test", "Environment": "dev"}


@pytest.mark.unit
class TestLoadConfigErrors:
    """Tests for load_config error handling."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing files."""
        config_file = tmp_path / "nonexistent.yml"
        with pytest.raises(FileNotFoundError):
            load_config(config_file)

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for invalid YAML."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("invalid: yaml: syntax:")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_file)

    def test_missing_required_field(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for missing required fields."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
""")
        with pytest.raises(ConfigError, match="Missing required fields"):
            load_config(config_file)

    def test_empty_subnet_ids(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for empty subnet_ids."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: ami-12345
subnet_ids: []
instance_types:
  - t3.micro
""")
        with pytest.raises(ConfigError, match="subnet_ids must be a non-empty list"):
            load_config(config_file)

    def test_empty_instance_types(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for empty instance_types."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: ami-12345
subnet_ids:
  - subnet-1
instance_types: []
""")
        with pytest.raises(ConfigError, match="instance_types must be a non-empty list"):
            load_config(config_file)

    def test_invalid_platform(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for invalid platform."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: ami-12345
subnet_ids:
  - subnet-1
instance_types:
  - t3.micro
platform: macos
""")
        with pytest.raises(ConfigError, match="Invalid platform"):
            load_config(config_file)

    def test_invalid_tags_type(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for invalid tags type."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: ami-12345
subnet_ids:
  - subnet-1
instance_types:
  - t3.micro
tags:
  - Name=test
""")
        with pytest.raises(ConfigError, match="tags must be a dictionary"):
            load_config(config_file)

    def test_not_a_mapping(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised when config is not a mapping."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("- item1\n- item2")
        with pytest.raises(ConfigError, match="Configuration must be a YAML mapping"):
            load_config(config_file)


@pytest.mark.unit
class TestLoadConfigWindowsPlatform:
    """Tests for load_config with windows platform."""

    def test_windows_platform(self, tmp_path: Path) -> None:
        """Test that windows platform is accepted."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: ami-12345
subnet_ids:
  - subnet-1
instance_types:
  - t3.micro
platform: windows
""")
        config = load_config(config_file)
        assert config.platform == "windows"

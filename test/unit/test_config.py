"""Unit tests for config module."""

from pathlib import Path

import pytest

from orfmi.config import AmiConfig, ConfigError, load_config


@pytest.mark.unit
class TestAmiConfig:
    """Tests for AmiConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are applied correctly."""
        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        assert config.ami_description == ""
        assert config.iam_instance_profile is None
        assert config.tags == {}
        assert config.ssh_username == "admin"
        assert config.ssh_timeout == 300
        assert config.ssh_retries == 30
        assert config.platform == "linux"

    def test_all_fields(self) -> None:
        """Test that all fields are set correctly."""
        config = AmiConfig(
            ami_name="test-ami",
            region="us-west-2",
            source_ami="ami-67890",
            subnet_ids=["subnet-1", "subnet-2"],
            instance_types=["t3.micro", "t3.small"],
            ami_description="Test AMI",
            iam_instance_profile="my-profile",
            tags={"Name": "test"},
            ssh_username="ec2-user",
            ssh_timeout=600,
            ssh_retries=60,
            platform="windows",
        )
        assert config.ami_name == "test-ami"
        assert config.region == "us-west-2"
        assert config.source_ami == "ami-67890"
        assert config.subnet_ids == ["subnet-1", "subnet-2"]
        assert config.instance_types == ["t3.micro", "t3.small"]
        assert config.ami_description == "Test AMI"
        assert config.iam_instance_profile == "my-profile"
        assert config.tags == {"Name": "test"}
        assert config.ssh_username == "ec2-user"
        assert config.ssh_timeout == 600
        assert config.ssh_retries == 60
        assert config.platform == "windows"

    def test_frozen(self) -> None:
        """Test that config is immutable."""
        config = AmiConfig(
            ami_name="test-ami",
            region="us-east-1",
            source_ami="ami-12345",
            subnet_ids=["subnet-1"],
            instance_types=["t3.micro"],
        )
        with pytest.raises(AttributeError):
            config.ami_name = "new-name"


@pytest.mark.unit
class TestLoadConfig:
    """Tests for load_config function."""

    def test_valid_minimal_config(self, tmp_path: Path) -> None:
        """Test loading a minimal valid configuration."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
""")
        config = load_config(config_file)
        assert config.ami_name == "test-ami"
        assert config.region == "us-east-1"
        assert config.source_ami == "debian-12-*"
        assert config.subnet_ids == ["subnet-12345"]
        assert config.instance_types == ["t3.micro"]

    def test_valid_full_config(self, tmp_path: Path) -> None:
        """Test loading a full configuration."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: my-ami
region: us-west-2
source_ami: ubuntu-22.04-*
subnet_ids:
  - subnet-1
  - subnet-2
instance_types:
  - t3.micro
  - t3.small
ami_description: My custom AMI
iam_instance_profile: my-profile
ssh_username: ubuntu
ssh_timeout: 600
ssh_retries: 60
platform: linux
tags:
  Name: test
  Environment: dev
""")
        config = load_config(config_file)
        assert config.ami_name == "my-ami"
        assert config.ami_description == "My custom AMI"
        assert config.iam_instance_profile == "my-profile"
        assert config.ssh_username == "ubuntu"
        assert config.ssh_timeout == 600
        assert config.ssh_retries == 60
        assert config.platform == "linux"
        assert config.tags == {"Name": "test", "Environment": "dev"}

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

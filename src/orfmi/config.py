"""Configuration file parsing for ORFMI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SSHSettings:
    """SSH connection settings."""

    username: str = "admin"
    timeout: int = 300
    retries: int = 30


@dataclass(frozen=True)
class InstanceSettings:
    """Instance launch settings."""

    subnet_ids: list[str]
    instance_types: list[str]
    security_group_id: str
    iam_instance_profile: str | None = None
    purchase_type: str = "on-demand"
    max_retries: int = 3


@dataclass(frozen=True)
class AmiIdentity:
    """AMI identification settings."""

    name: str
    description: str = ""


@dataclass(frozen=True)
class AmiConfig:
    """Configuration for AMI creation."""

    ami: AmiIdentity
    region: str
    source_ami: str
    instance: InstanceSettings
    tags: dict[str, str] = field(default_factory=dict)
    ssh: SSHSettings = field(default_factory=SSHSettings)
    platform: str = "linux"


class ConfigError(Exception):
    """Exception raised for configuration errors."""


def _validate_required_fields(data: dict[str, Any]) -> None:
    """Validate that all required fields are present."""
    required = [
        "ami_name",
        "region",
        "source_ami",
        "subnet_ids",
        "instance_types",
        "security_group_id",
    ]
    missing = [f for f in required if f not in data or data[f] is None]
    if missing:
        raise ConfigError(f"Missing required fields: {', '.join(missing)}")


def _validate_list_fields(data: dict[str, Any]) -> None:
    """Validate that list fields contain valid values."""
    if not isinstance(data.get("subnet_ids"), list) or not data["subnet_ids"]:
        raise ConfigError("subnet_ids must be a non-empty list")
    if not isinstance(data.get("instance_types"), list) or not data["instance_types"]:
        raise ConfigError("instance_types must be a non-empty list")


def _validate_platform(data: dict[str, Any]) -> None:
    """Validate platform field."""
    platform = data.get("platform", "linux")
    if platform not in ("linux", "windows"):
        raise ConfigError(f"Invalid platform: {platform}. Must be 'linux' or 'windows'")


def _validate_purchase_type(data: dict[str, Any]) -> None:
    """Validate purchase_type field."""
    purchase_type = data.get("purchase_type", "on-demand")
    if purchase_type not in ("on-demand", "spot"):
        raise ConfigError(
            f"Invalid purchase_type: {purchase_type}. Must be 'on-demand' or 'spot'"
        )


def _parse_tags(data: dict[str, Any]) -> dict[str, str]:
    """Parse tags from configuration data."""
    tags = data.get("tags", {})
    if not isinstance(tags, dict):
        raise ConfigError("tags must be a dictionary")
    return {str(k): str(v) for k, v in tags.items()}


def load_config(config_path: Path) -> AmiConfig:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        AmiConfig object with validated configuration.

    Raises:
        ConfigError: If the configuration is invalid.
        FileNotFoundError: If the configuration file doesn't exist.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in configuration file: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a YAML mapping")

    _validate_required_fields(data)
    _validate_list_fields(data)
    _validate_platform(data)
    _validate_purchase_type(data)

    ssh_settings = SSHSettings(
        username=str(data.get("ssh_username", "admin")),
        timeout=int(data.get("ssh_timeout", 300)),
        retries=int(data.get("ssh_retries", 30)),
    )
    instance_settings = InstanceSettings(
        subnet_ids=[str(s) for s in data["subnet_ids"]],
        instance_types=[str(t) for t in data["instance_types"]],
        security_group_id=str(data["security_group_id"]),
        iam_instance_profile=data.get("iam_instance_profile"),
        purchase_type=str(data.get("purchase_type", "on-demand")),
        max_retries=int(data.get("max_retries", 3)),
    )
    ami_identity = AmiIdentity(
        name=str(data["ami_name"]),
        description=str(data.get("ami_description", "")),
    )
    return AmiConfig(
        ami=ami_identity,
        region=str(data["region"]),
        source_ami=str(data["source_ami"]),
        instance=instance_settings,
        tags=_parse_tags(data),
        ssh=ssh_settings,
        platform=str(data.get("platform", "linux")),
    )

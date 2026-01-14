"""AMI builder orchestration."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import AmiConfig
from .ec2 import (
    FleetConfig,
    LaunchTemplateParams,
    create_ami,
    create_ec2_client,
    create_fleet_instance,
    create_key_pair,
    create_launch_template,
    create_security_group,
    delete_key_pair,
    delete_launch_template,
    delete_security_group,
    generate_unique_id,
    get_vpc_from_subnet,
    lookup_source_ami,
    terminate_instance,
    wait_for_instance,
)
from .ssh import SshConfig, run_setup_script

logger = logging.getLogger(__name__)


@dataclass
class BuildState:
    """Mutable state tracking for the AMI build process."""

    instance_id: str | None = None
    sg_id: str | None = None
    key_material: str | None = None
    result: str | None = None


@dataclass
class BuildContext:
    """Immutable context for the AMI build process."""

    ec2: Any
    config: AmiConfig
    setup_script: Path
    unique_id: str
    extra_files: list[Path] = field(default_factory=list)

    def resource_name(self, suffix: str = "") -> str:
        """Generate a resource name with optional suffix."""
        base = f"orfmi-{self.unique_id}"
        return f"{base}-{suffix}" if suffix else base


class AmiBuilder:
    """Builder for creating AWS AMIs."""

    def __init__(
        self,
        config: AmiConfig,
        setup_script: Path,
        extra_files: list[Path] | None = None,
    ) -> None:
        """Initialize the AMI builder.

        Args:
            config: AMI configuration.
            setup_script: Path to the setup script.
            extra_files: Optional list of additional files to upload.
        """
        self.config = config
        self.setup_script = setup_script
        self.extra_files = extra_files or []

    def validate(self) -> bool:
        """Validate the build configuration.

        Returns:
            True if configuration is valid for building.
        """
        return bool(
            self.config.ami.name
            and self.config.region
            and self.config.source_ami
            and self.config.instance.subnet_ids
            and self.config.instance.instance_types
        )

    def build(self) -> str:
        """Build the AMI.

        Returns:
            The AMI ID.

        Raises:
            RuntimeError: If the build fails.
        """
        unique_id = generate_unique_id()
        ec2 = create_ec2_client(self.config.region)
        ctx = BuildContext(
            ec2=ec2,
            config=self.config,
            setup_script=self.setup_script,
            unique_id=unique_id,
            extra_files=self.extra_files,
        )
        state = BuildState()

        try:
            self._run_build(ctx, state)
        finally:
            self._cleanup(ctx, state)

        if not state.result:
            raise RuntimeError("AMI build failed: no AMI ID returned")

        return state.result

    def _run_build(self, ctx: BuildContext, state: BuildState) -> None:
        """Execute the AMI build process."""
        config = ctx.config
        ec2 = ctx.ec2
        key_name = ctx.resource_name()
        template_name = ctx.resource_name()
        sg_name = ctx.resource_name()

        logger.info("Subnets: %s", config.instance.subnet_ids)
        vpc_id = get_vpc_from_subnet(ec2, config.instance.subnet_ids[0])
        logger.info("VPC: %s", vpc_id)

        logger.info("Creating temporary key pair...")
        state.key_material = create_key_pair(ec2, key_name, config.tags)

        logger.info("Creating temporary security group...")
        state.sg_id = create_security_group(
            ec2, vpc_id, sg_name, config.tags, config.platform
        )

        logger.info("Looking up source AMI: %s", config.source_ami)
        source_ami_id = lookup_source_ami(ec2, config.source_ami)
        logger.info("Found source AMI ID: %s", source_ami_id)

        logger.info("Creating launch template...")
        lt_params = LaunchTemplateParams(
            template_name=template_name,
            base_ami=source_ami_id,
            sg_id=state.sg_id,
            key_name=key_name,
            iam_profile=config.instance.iam_instance_profile,
        )
        create_launch_template(ec2, lt_params, config.tags)

        self._launch_and_configure(ctx, state, template_name)

        if not state.instance_id:
            raise RuntimeError("Instance ID not set after launch")

        state.result = create_ami(
            ec2,
            state.instance_id,
            config.ami.name,
            config.ami.description,
            config.tags,
        )

    def _launch_and_configure(
        self, ctx: BuildContext, state: BuildState, template_name: str
    ) -> None:
        """Launch instance and run configuration."""
        config = ctx.config
        ec2 = ctx.ec2

        num_types = len(config.instance.instance_types)
        num_subnets = len(config.instance.subnet_ids)
        logger.info(
            "Creating EC2 Fleet with %d instance types x %d subnets...",
            num_types,
            num_subnets,
        )
        fleet_config = FleetConfig(
            instance_types=config.instance.instance_types,
            subnet_ids=config.instance.subnet_ids,
        )
        state.instance_id = create_fleet_instance(ec2, template_name, fleet_config)
        logger.info("Instance launched: %s", state.instance_id)

        public_ip = wait_for_instance(ec2, state.instance_id)
        logger.info("Instance ready at %s", public_ip)

        if ctx.setup_script.exists():
            if not state.key_material:
                raise RuntimeError("Key material not set")

            logger.info("Running setup script...")
            ssh_config = SshConfig(
                ip_address=public_ip,
                key_material=state.key_material,
                username=config.ssh.username,
                timeout=config.ssh.timeout,
                retries=config.ssh.retries,
            )
            run_setup_script(ssh_config, ctx.setup_script, ctx.extra_files)

    def _cleanup(self, ctx: BuildContext, state: BuildState) -> None:
        """Clean up temporary resources created during the build."""
        ec2 = ctx.ec2
        key_name = ctx.resource_name()
        template_name = ctx.resource_name()

        if state.instance_id:
            logger.info("Terminating temporary instance...")
            terminate_instance(ec2, state.instance_id)
            logger.info("Temporary instance terminated.")

        delete_launch_template(ec2, template_name)

        logger.info("Deleting temporary key pair...")
        delete_key_pair(ec2, key_name)
        logger.info("Temporary key pair deleted.")

        if state.sg_id:
            logger.info("Deleting temporary security group...")
            delete_security_group(ec2, state.sg_id)
            logger.info("Temporary security group deleted.")

"""EC2 operations for AMI building."""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

RETRIABLE_ERROR_CODES = frozenset({
    "InsufficientInstanceCapacity",
    "InsufficientCapacity",
    "InstanceLimitExceeded",
    "MaxSpotInstanceCountExceeded",
    "RequestLimitExceeded",
    "ServiceUnavailable",
})


class CapacityError(Exception):
    """Raised when instance creation fails due to capacity issues."""


class InstanceTerminatedError(Exception):
    """Raised when instance is no longer running."""


@dataclass
class LaunchTemplateParams:
    """Parameters for creating an EC2 launch template."""

    template_name: str
    base_ami: str
    sg_id: str
    key_name: str
    iam_profile: str | None


@dataclass
class FleetConfig:
    """Configuration for EC2 Fleet instance creation."""

    instance_types: list[str]
    subnet_ids: list[str]
    allocation_strategy: str = "lowest-price"
    purchase_type: str = "on-demand"


def is_capacity_error(errors: list[dict[str, Any]]) -> bool:
    """Check if any error is capacity-related."""
    return any(e.get("ErrorCode") in RETRIABLE_ERROR_CODES for e in errors)


def get_vpc_from_subnet(ec2: Any, subnet_id: str) -> str:
    """Get the VPC ID from a subnet ID."""
    response = ec2.describe_subnets(SubnetIds=[subnet_id])
    return str(response["Subnets"][0]["VpcId"])


def lookup_source_ami(ec2: Any, ami_name: str) -> str:
    """Look up an AMI ID by name.

    Searches for AMIs by name across all owners.

    Args:
        ec2: boto3 EC2 client.
        ami_name: The name of the AMI to look up.

    Returns:
        The AMI ID.

    Raises:
        RuntimeError: If no AMI is found with the given name.
    """
    response = ec2.describe_images(
        Filters=[{"Name": "name", "Values": [ami_name]}],
    )
    if not response["Images"]:
        raise RuntimeError(f"No AMI found with name: {ami_name}")
    images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
    return str(images[0]["ImageId"])


def create_key_pair(ec2: Any, key_name: str, tags: dict[str, str]) -> str:
    """Create an EC2 key pair and return the private key material."""
    tag_specs = []
    if tags:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        tag_specs = [{"ResourceType": "key-pair", "Tags": tag_list}]
    response = ec2.create_key_pair(
        KeyName=key_name, KeyType="ed25519", TagSpecifications=tag_specs
    )
    return str(response["KeyMaterial"])


def delete_key_pair(ec2: Any, key_name: str) -> None:
    """Delete an EC2 key pair."""
    try:
        ec2.delete_key_pair(KeyName=key_name)
    except ClientError as e:
        logger.warning("Failed to delete key pair %s: %s", key_name, e)


def create_security_group(
    ec2: Any, vpc_id: str, group_name: str, tags: dict[str, str], platform: str
) -> str:
    """Create a security group with SSH or RDP access."""
    tag_specs = []
    if tags:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        tag_specs = [{"ResourceType": "security-group", "Tags": tag_list}]
    response = ec2.create_security_group(
        GroupName=group_name,
        Description="Temporary SG for AMI builder",
        VpcId=vpc_id,
        TagSpecifications=tag_specs,
    )
    sg_id = response["GroupId"]
    port = 3389 if platform == "windows" else 22
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": port,
                "ToPort": port,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    )
    return str(sg_id)


def delete_security_group(ec2: Any, sg_id: str) -> None:
    """Delete a security group with retry logic."""
    for attempt in range(12):
        try:
            ec2.delete_security_group(GroupId=sg_id)
            return
        except ClientError as e:
            if attempt == 11:
                logger.warning("Failed to delete security group %s: %s", sg_id, e)
                return
            time.sleep(5)


def create_launch_template(
    ec2: Any, params: LaunchTemplateParams, tags: dict[str, str]
) -> None:
    """Create an EC2 launch template."""
    data: dict[str, Any] = {
        "ImageId": params.base_ami,
        "KeyName": params.key_name,
        "SecurityGroupIds": [params.sg_id],
    }
    if params.iam_profile:
        data["IamInstanceProfile"] = {"Name": params.iam_profile}
    if tags:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        data["TagSpecifications"] = [{"ResourceType": "instance", "Tags": tag_list}]
    tag_specs = []
    if tags:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        tag_specs = [{"ResourceType": "launch-template", "Tags": tag_list}]
    ec2.create_launch_template(
        LaunchTemplateName=params.template_name,
        LaunchTemplateData=data,
        TagSpecifications=tag_specs,
    )


def delete_launch_template(ec2: Any, template_name: str) -> None:
    """Delete an EC2 launch template."""
    try:
        ec2.delete_launch_template(LaunchTemplateName=template_name)
    except ClientError:
        pass


def create_fleet_instance(
    ec2: Any, template_name: str, config: FleetConfig
) -> str:
    """Create a fleet instance using the specified template.

    Returns:
        The instance ID of the created instance.

    Raises:
        CapacityError: If instance creation fails due to capacity issues.
        RuntimeError: If no instance was created for other reasons.
    """
    response = ec2.describe_launch_templates(LaunchTemplateNames=[template_name])
    template_id = response["LaunchTemplates"][0]["LaunchTemplateId"]

    overrides = [
        {"InstanceType": t, "SubnetId": s}
        for t in config.instance_types
        for s in config.subnet_ids
    ]

    fleet_params: dict[str, Any] = {
        "LaunchTemplateConfigs": [
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": template_id,
                    "Version": "$Latest",
                },
                "Overrides": overrides,
            }
        ],
        "TargetCapacitySpecification": {
            "TotalTargetCapacity": 1,
            "DefaultTargetCapacityType": config.purchase_type,
        },
        "Type": "instant",
    }

    if config.purchase_type == "spot":
        fleet_params["SpotOptions"] = {
            "AllocationStrategy": config.allocation_strategy,
            "InstanceInterruptionBehavior": "terminate",
        }
    else:
        fleet_params["OnDemandOptions"] = {
            "AllocationStrategy": config.allocation_strategy,
        }

    fleet_response = ec2.create_fleet(**fleet_params)

    instances = fleet_response.get("Instances", [])
    if not instances:
        errors = fleet_response.get("Errors", [])
        error_msg = "; ".join(str(e) for e in errors) if errors else "Unknown error"
        if is_capacity_error(errors):
            raise CapacityError(f"Capacity error creating instance: {error_msg}")
        raise RuntimeError(f"Failed to create fleet instance: {error_msg}")

    return str(instances[0]["InstanceIds"][0])


def wait_for_instance_running(ec2: Any, instance_id: str) -> None:
    """Wait for an EC2 instance to reach running state."""
    logger.info("Waiting for instance %s to be running...", instance_id)
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])
    logger.info("Instance is running")


def wait_for_status_checks(ec2: Any, instance_id: str) -> None:
    """Wait for EC2 instance status checks to pass."""
    logger.info("Waiting for status checks to pass...")
    waiter = ec2.get_waiter("instance_status_ok")
    waiter.wait(InstanceIds=[instance_id])
    logger.info("All status checks passed")


def get_instance_public_ip(ec2: Any, instance_id: str) -> str:
    """Get the public IP address of an EC2 instance."""
    response = ec2.describe_instances(InstanceIds=[instance_id])
    return str(response["Reservations"][0]["Instances"][0]["PublicIpAddress"])


def check_instance_state(ec2: Any, instance_id: str) -> None:
    """Verify instance is still running.

    Args:
        ec2: boto3 EC2 client.
        instance_id: The instance ID to check.

    Raises:
        InstanceTerminatedError: If instance is not in running state.
    """
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instance = response["Reservations"][0]["Instances"][0]
    state = instance["State"]["Name"]

    if state != "running":
        reason = instance.get("StateReason", {}).get("Message", "Unknown")
        raise InstanceTerminatedError(
            f"Instance {instance_id} is {state}: {reason}"
        )


def wait_for_instance(ec2: Any, instance_id: str) -> str:
    """Wait for instance to be running and status checks to pass.

    Returns:
        The public IP address of the instance.
    """
    wait_for_instance_running(ec2, instance_id)
    wait_for_status_checks(ec2, instance_id)
    return get_instance_public_ip(ec2, instance_id)


def create_ami(
    ec2: Any, instance_id: str, ami_name: str, ami_description: str, tags: dict[str, str]
) -> str:
    """Create an AMI from an instance and apply tags.

    Returns:
        The AMI ID.
    """
    response = ec2.create_image(
        InstanceId=instance_id, Name=ami_name, Description=ami_description or ""
    )
    ami_id: str = response["ImageId"]
    logger.info("Creating AMI %s...", ami_id)
    waiter = ec2.get_waiter("image_available")
    waiter.wait(ImageIds=[ami_id])
    logger.info("AMI %s created.", ami_id)
    if tags:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        ec2.create_tags(Resources=[ami_id], Tags=tag_list)
        image = ec2.describe_images(ImageIds=[ami_id])["Images"][0]
        snapshots = image.get("BlockDeviceMappings", [])
        for bdm in snapshots:
            if "Ebs" in bdm:
                ec2.create_tags(Resources=[bdm["Ebs"]["SnapshotId"]], Tags=tag_list)
    return ami_id


def terminate_instance(ec2: Any, instance_id: str) -> None:
    """Terminate an EC2 instance and wait for termination."""
    ec2.terminate_instances(InstanceIds=[instance_id])
    waiter = ec2.get_waiter("instance_terminated")
    waiter.wait(InstanceIds=[instance_id], WaiterConfig={"Delay": 15, "MaxAttempts": 40})


def generate_unique_id() -> str:
    """Generate a unique identifier for temporary resources."""
    return uuid.uuid4().hex[:8]


def create_ec2_client(region: str) -> Any:
    """Create a boto3 EC2 client for the specified region."""
    return boto3.client("ec2", region_name=region)

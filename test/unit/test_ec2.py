"""Unit tests for EC2 module."""

from unittest.mock import MagicMock, patch

import pytest

from orfmi.ec2 import (
    FleetConfig,
    LaunchTemplateParams,
    create_ami,
    create_fleet_instance,
    create_key_pair,
    create_launch_template,
    create_security_group,
    delete_key_pair,
    delete_launch_template,
    delete_security_group,
    generate_unique_id,
    get_instance_public_ip,
    get_vpc_from_subnet,
    lookup_source_ami,
    terminate_instance,
    wait_for_instance,
    wait_for_instance_running,
    wait_for_status_checks,
)


@pytest.mark.unit
class TestGetVpcFromSubnet:
    """Tests for get_vpc_from_subnet function."""

    def test_returns_vpc_id(self) -> None:
        """Test that VPC ID is returned from subnet."""
        ec2 = MagicMock()
        ec2.describe_subnets.return_value = {
            "Subnets": [{"VpcId": "vpc-12345"}]
        }
        result = get_vpc_from_subnet(ec2, "subnet-12345")
        assert result == "vpc-12345"
        ec2.describe_subnets.assert_called_once_with(SubnetIds=["subnet-12345"])


@pytest.mark.unit
class TestLookupSourceAmi:
    """Tests for lookup_source_ami function."""

    def test_returns_ami_id(self) -> None:
        """Test that AMI ID is returned."""
        ec2 = MagicMock()
        ec2.describe_images.return_value = {
            "Images": [
                {"ImageId": "ami-12345", "CreationDate": "2024-01-01"},
            ]
        }
        result = lookup_source_ami(ec2, "test-ami-*")
        assert result == "ami-12345"

    def test_returns_newest_ami(self) -> None:
        """Test that the newest AMI is returned when multiple match."""
        ec2 = MagicMock()
        ec2.describe_images.return_value = {
            "Images": [
                {"ImageId": "ami-old", "CreationDate": "2024-01-01"},
                {"ImageId": "ami-new", "CreationDate": "2024-06-01"},
            ]
        }
        result = lookup_source_ami(ec2, "test-ami-*")
        assert result == "ami-new"

    def test_raises_when_no_ami_found(self) -> None:
        """Test that RuntimeError is raised when no AMI found."""
        ec2 = MagicMock()
        ec2.describe_images.return_value = {"Images": []}
        with pytest.raises(RuntimeError, match="No AMI found"):
            lookup_source_ami(ec2, "nonexistent-ami")


@pytest.mark.unit
class TestCreateKeyPair:
    """Tests for create_key_pair function."""

    def test_creates_key_pair_with_tags(self) -> None:
        """Test key pair creation with tags."""
        ec2 = MagicMock()
        ec2.create_key_pair.return_value = {"KeyMaterial": "private-key-data"}
        result = create_key_pair(ec2, "test-key", {"Name": "test"})
        assert result == "private-key-data"
        ec2.create_key_pair.assert_called_once()

    def test_creates_key_pair_without_tags(self) -> None:
        """Test key pair creation without tags."""
        ec2 = MagicMock()
        ec2.create_key_pair.return_value = {"KeyMaterial": "private-key-data"}
        result = create_key_pair(ec2, "test-key", {})
        assert result == "private-key-data"


@pytest.mark.unit
class TestDeleteKeyPair:
    """Tests for delete_key_pair function."""

    def test_deletes_key_pair(self) -> None:
        """Test successful key pair deletion."""
        ec2 = MagicMock()
        delete_key_pair(ec2, "test-key")
        ec2.delete_key_pair.assert_called_once_with(KeyName="test-key")

    def test_handles_error(self) -> None:
        """Test that errors are logged but not raised."""
        from botocore.exceptions import ClientError
        ec2 = MagicMock()
        ec2.delete_key_pair.side_effect = ClientError(
            {"Error": {"Code": "InvalidKeyPair.NotFound"}}, "DeleteKeyPair"
        )
        delete_key_pair(ec2, "test-key")


@pytest.mark.unit
class TestCreateSecurityGroup:
    """Tests for create_security_group function."""

    def test_creates_linux_security_group(self) -> None:
        """Test security group creation for Linux (SSH)."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        result = create_security_group(ec2, "vpc-12345", "test-sg", {}, "linux")
        assert result == "sg-12345"
        ec2.authorize_security_group_ingress.assert_called_once()
        call_kwargs = ec2.authorize_security_group_ingress.call_args.kwargs
        assert call_kwargs["IpPermissions"][0]["FromPort"] == 22

    def test_creates_windows_security_group(self) -> None:
        """Test security group creation for Windows (RDP)."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        result = create_security_group(ec2, "vpc-12345", "test-sg", {}, "windows")
        assert result == "sg-12345"
        call_kwargs = ec2.authorize_security_group_ingress.call_args.kwargs
        assert call_kwargs["IpPermissions"][0]["FromPort"] == 3389


@pytest.mark.unit
class TestDeleteSecurityGroup:
    """Tests for delete_security_group function."""

    def test_deletes_security_group(self) -> None:
        """Test successful security group deletion."""
        ec2 = MagicMock()
        delete_security_group(ec2, "sg-12345")
        ec2.delete_security_group.assert_called_once_with(GroupId="sg-12345")

    def test_retries_on_failure(self) -> None:
        """Test that deletion is retried on failure."""
        from botocore.exceptions import ClientError
        ec2 = MagicMock()
        ec2.delete_security_group.side_effect = [
            ClientError({"Error": {"Code": "DependencyViolation"}}, "DeleteSecurityGroup"),
            None,
        ]
        with patch("time.sleep"):
            delete_security_group(ec2, "sg-12345")
        assert ec2.delete_security_group.call_count == 2


@pytest.mark.unit
class TestCreateLaunchTemplate:
    """Tests for create_launch_template function."""

    def test_creates_template_with_all_params(self) -> None:
        """Test launch template creation with all parameters."""
        ec2 = MagicMock()
        params = LaunchTemplateParams(
            template_name="test-template",
            base_ami="ami-12345",
            sg_id="sg-12345",
            key_name="test-key",
            iam_profile="test-profile",
        )
        create_launch_template(ec2, params, {"Name": "test"})
        ec2.create_launch_template.assert_called_once()

    def test_creates_template_without_iam_profile(self) -> None:
        """Test launch template creation without IAM profile."""
        ec2 = MagicMock()
        params = LaunchTemplateParams(
            template_name="test-template",
            base_ami="ami-12345",
            sg_id="sg-12345",
            key_name="test-key",
            iam_profile=None,
        )
        create_launch_template(ec2, params, {})
        ec2.create_launch_template.assert_called_once()


@pytest.mark.unit
class TestDeleteLaunchTemplate:
    """Tests for delete_launch_template function."""

    def test_deletes_template(self) -> None:
        """Test successful template deletion."""
        ec2 = MagicMock()
        delete_launch_template(ec2, "test-template")
        ec2.delete_launch_template.assert_called_once()

    def test_handles_error(self) -> None:
        """Test that errors are silently ignored."""
        from botocore.exceptions import ClientError
        ec2 = MagicMock()
        ec2.delete_launch_template.side_effect = ClientError(
            {"Error": {"Code": "NotFound"}}, "DeleteLaunchTemplate"
        )
        delete_launch_template(ec2, "test-template")


@pytest.mark.unit
class TestCreateFleetInstance:
    """Tests for create_fleet_instance function."""

    def test_creates_instance(self) -> None:
        """Test fleet instance creation."""
        ec2 = MagicMock()
        ec2.describe_launch_templates.return_value = {
            "LaunchTemplates": [{"LaunchTemplateId": "lt-12345"}]
        }
        ec2.create_fleet.return_value = {
            "Instances": [{"InstanceIds": ["i-12345"]}]
        }
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
        )
        result = create_fleet_instance(ec2, "test-template", config)
        assert result == "i-12345"

    def test_raises_when_no_instance_created(self) -> None:
        """Test that RuntimeError is raised when no instance created."""
        ec2 = MagicMock()
        ec2.describe_launch_templates.return_value = {
            "LaunchTemplates": [{"LaunchTemplateId": "lt-12345"}]
        }
        ec2.create_fleet.return_value = {
            "Instances": [],
            "Errors": [{"ErrorMessage": "Capacity error"}],
        }
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
        )
        with pytest.raises(RuntimeError, match="Failed to create fleet instance"):
            create_fleet_instance(ec2, "test-template", config)


@pytest.mark.unit
class TestWaitFunctions:
    """Tests for wait functions."""

    def test_wait_for_instance_running(self) -> None:
        """Test waiting for instance to be running."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_instance_running(ec2, "i-12345")
        ec2.get_waiter.assert_called_once_with("instance_running")
        waiter.wait.assert_called_once()

    def test_wait_for_status_checks(self) -> None:
        """Test waiting for status checks."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_status_checks(ec2, "i-12345")
        ec2.get_waiter.assert_called_once_with("instance_status_ok")
        waiter.wait.assert_called_once()

    def test_wait_for_instance(self) -> None:
        """Test waiting for instance to be ready."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"PublicIpAddress": "1.2.3.4"}]}]
        }
        result = wait_for_instance(ec2, "i-12345")
        assert result == "1.2.3.4"


@pytest.mark.unit
class TestGetInstancePublicIp:
    """Tests for get_instance_public_ip function."""

    def test_returns_ip(self) -> None:
        """Test that public IP is returned."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"PublicIpAddress": "1.2.3.4"}]}]
        }
        result = get_instance_public_ip(ec2, "i-12345")
        assert result == "1.2.3.4"


@pytest.mark.unit
class TestCreateAmi:
    """Tests for create_ami function."""

    def test_creates_ami(self) -> None:
        """Test AMI creation."""
        ec2 = MagicMock()
        ec2.create_image.return_value = {"ImageId": "ami-12345"}
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        ec2.describe_images.return_value = {
            "Images": [{"BlockDeviceMappings": []}]
        }
        result = create_ami(ec2, "i-12345", "test-ami", "Test AMI", {})
        assert result == "ami-12345"

    def test_creates_ami_with_tags(self) -> None:
        """Test AMI creation with tags."""
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
        result = create_ami(ec2, "i-12345", "test-ami", "Test AMI", {"Name": "test"})
        assert result == "ami-12345"
        assert ec2.create_tags.call_count == 2


@pytest.mark.unit
class TestTerminateInstance:
    """Tests for terminate_instance function."""

    def test_terminates_instance(self) -> None:
        """Test instance termination."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        terminate_instance(ec2, "i-12345")
        ec2.terminate_instances.assert_called_once_with(InstanceIds=["i-12345"])
        waiter.wait.assert_called_once()


@pytest.mark.unit
class TestGenerateUniqueId:
    """Tests for generate_unique_id function."""

    def test_generates_unique_ids(self) -> None:
        """Test that unique IDs are generated."""
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        assert id1 != id2
        assert len(id1) == 8
        assert len(id2) == 8

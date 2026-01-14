"""Unit tests for EC2 module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from orfmi.ec2 import (
    CapacityError,
    FleetConfig,
    InstanceTerminatedError,
    LaunchTemplateParams,
    check_instance_state,
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
    get_instance_public_ip,
    get_vpc_from_subnet,
    is_capacity_error,
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

    def test_calls_describe_subnets(self) -> None:
        """Test that describe_subnets is called correctly."""
        ec2 = MagicMock()
        ec2.describe_subnets.return_value = {"Subnets": [{"VpcId": "vpc-abc"}]}
        get_vpc_from_subnet(ec2, "subnet-xyz")
        assert ec2.describe_subnets.call_args.kwargs == {"SubnetIds": ["subnet-xyz"]}


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

    def test_creates_key_pair_calls_api(self) -> None:
        """Test key pair creation calls API."""
        ec2 = MagicMock()
        ec2.create_key_pair.return_value = {"KeyMaterial": "private-key-data"}
        create_key_pair(ec2, "test-key", {"Name": "test"})
        assert ec2.create_key_pair.call_count == 1

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
        assert ec2.delete_key_pair.call_args.kwargs == {"KeyName": "test-key"}

    def test_handles_error(self) -> None:
        """Test that errors are logged but not raised."""
        ec2 = MagicMock()
        ec2.delete_key_pair.side_effect = ClientError(
            {"Error": {"Code": "InvalidKeyPair.NotFound"}}, "DeleteKeyPair"
        )
        delete_key_pair(ec2, "test-key")
        assert ec2.delete_key_pair.call_count == 1


@pytest.mark.unit
class TestCreateSecurityGroup:
    """Tests for create_security_group function."""

    def test_creates_linux_security_group_returns_id(self) -> None:
        """Test security group creation for Linux returns ID."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        result = create_security_group(ec2, "vpc-12345", "test-sg", {}, "linux")
        assert result == "sg-12345"

    def test_creates_linux_security_group_uses_ssh_port(self) -> None:
        """Test security group creation for Linux uses SSH port."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        create_security_group(ec2, "vpc-12345", "test-sg", {}, "linux")
        call_kwargs = ec2.authorize_security_group_ingress.call_args.kwargs
        assert call_kwargs["IpPermissions"][0]["FromPort"] == 22

    def test_creates_windows_security_group_returns_id(self) -> None:
        """Test security group creation for Windows returns ID."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        result = create_security_group(ec2, "vpc-12345", "test-sg", {}, "windows")
        assert result == "sg-12345"

    def test_creates_windows_security_group_uses_rdp_port(self) -> None:
        """Test security group creation for Windows uses RDP port."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        create_security_group(ec2, "vpc-12345", "test-sg", {}, "windows")
        call_kwargs = ec2.authorize_security_group_ingress.call_args.kwargs
        assert call_kwargs["IpPermissions"][0]["FromPort"] == 3389


@pytest.mark.unit
class TestDeleteSecurityGroup:
    """Tests for delete_security_group function."""

    def test_deletes_security_group(self) -> None:
        """Test successful security group deletion."""
        ec2 = MagicMock()
        delete_security_group(ec2, "sg-12345")
        assert ec2.delete_security_group.call_args.kwargs == {"GroupId": "sg-12345"}

    def test_retries_on_failure(self) -> None:
        """Test that deletion is retried on failure."""
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
        assert ec2.create_launch_template.call_count == 1

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
        assert ec2.create_launch_template.call_count == 1


@pytest.mark.unit
class TestDeleteLaunchTemplate:
    """Tests for delete_launch_template function."""

    def test_deletes_template(self) -> None:
        """Test successful template deletion."""
        ec2 = MagicMock()
        delete_launch_template(ec2, "test-template")
        assert ec2.delete_launch_template.call_count == 1

    def test_handles_error(self) -> None:
        """Test that errors are silently ignored."""
        ec2 = MagicMock()
        ec2.delete_launch_template.side_effect = ClientError(
            {"Error": {"Code": "NotFound"}}, "DeleteLaunchTemplate"
        )
        delete_launch_template(ec2, "test-template")
        assert ec2.delete_launch_template.call_count == 1


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
class TestWaitForInstanceRunning:
    """Tests for wait_for_instance_running function."""

    def test_calls_get_waiter(self) -> None:
        """Test that get_waiter is called with correct waiter name."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_instance_running(ec2, "i-12345")
        assert ec2.get_waiter.call_args[0][0] == "instance_running"

    def test_calls_waiter_wait(self) -> None:
        """Test that waiter.wait is called."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_instance_running(ec2, "i-12345")
        assert waiter.wait.call_count == 1


@pytest.mark.unit
class TestWaitForStatusChecks:
    """Tests for wait_for_status_checks function."""

    def test_calls_get_waiter(self) -> None:
        """Test that get_waiter is called with correct waiter name."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_status_checks(ec2, "i-12345")
        assert ec2.get_waiter.call_args[0][0] == "instance_status_ok"

    def test_calls_waiter_wait(self) -> None:
        """Test that waiter.wait is called."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        wait_for_status_checks(ec2, "i-12345")
        assert waiter.wait.call_count == 1

    def test_wait_for_instance_returns_public_ip(self) -> None:
        """Test waiting for instance returns public IP."""
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

    def test_calls_describe_instances(self) -> None:
        """Test that describe_instances is called correctly."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"PublicIpAddress": "5.6.7.8"}]}]
        }
        get_instance_public_ip(ec2, "i-abc123")
        assert ec2.describe_instances.call_args.kwargs == {"InstanceIds": ["i-abc123"]}


@pytest.mark.unit
class TestCreateAmi:
    """Tests for create_ami function."""

    def test_creates_ami_returns_id(self) -> None:
        """Test AMI creation returns ID."""
        ec2 = MagicMock()
        ec2.create_image.return_value = {"ImageId": "ami-12345"}
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        ec2.describe_images.return_value = {
            "Images": [{"BlockDeviceMappings": []}]
        }
        result = create_ami(ec2, "i-12345", "test-ami", "Test AMI", {})
        assert result == "ami-12345"

    def test_creates_ami_with_tags_returns_id(
        self, create_ami_with_tags_mocks: dict[str, Any]
    ) -> None:
        """Test AMI creation with tags returns ID."""
        ec2 = create_ami_with_tags_mocks["ec2"]
        assert ec2.create_image.return_value == {"ImageId": "ami-12345"}

    def test_creates_ami_with_tags_calls_create_tags(
        self, create_ami_with_tags_mocks: dict[str, Any]
    ) -> None:
        """Test AMI creation with tags calls create_tags."""
        ec2 = create_ami_with_tags_mocks["ec2"]
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
        assert ec2.terminate_instances.call_args.kwargs == {"InstanceIds": ["i-12345"]}

    def test_waits_for_termination(self) -> None:
        """Test that waiter is used for termination."""
        ec2 = MagicMock()
        waiter = MagicMock()
        ec2.get_waiter.return_value = waiter
        terminate_instance(ec2, "i-abc")
        assert waiter.wait.call_count == 1


@pytest.mark.unit
class TestGenerateUniqueId:
    """Tests for generate_unique_id function."""

    def test_generates_unique_ids(self) -> None:
        """Test that unique IDs are generated."""
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        assert id1 != id2

    def test_id_length(self) -> None:
        """Test that IDs have correct length."""
        unique_id = generate_unique_id()
        assert len(unique_id) == 8


@pytest.mark.unit
class TestSecurityGroupWithTagsAndRetry:
    """Tests for create_security_group with tags and retry behavior."""

    def test_creates_security_group_with_tags(self) -> None:
        """Test security group creation with tags creates tag specs."""
        ec2 = MagicMock()
        ec2.create_security_group.return_value = {"GroupId": "sg-12345"}
        create_security_group(ec2, "vpc-12345", "test-sg", {"Name": "test"}, "linux")
        call_kwargs = ec2.create_security_group.call_args.kwargs
        assert call_kwargs["TagSpecifications"][0]["ResourceType"] == "security-group"

    def test_logs_warning_after_max_retries(self) -> None:
        """Test that warning is logged after all retries fail."""
        ec2 = MagicMock()
        ec2.delete_security_group.side_effect = ClientError(
            {"Error": {"Code": "DependencyViolation"}}, "DeleteSecurityGroup"
        )
        with patch("time.sleep"):
            delete_security_group(ec2, "sg-12345")
        assert ec2.delete_security_group.call_count == 12


@pytest.mark.unit
class TestCreateEc2Client:
    """Tests for create_ec2_client function."""

    @patch("orfmi.ec2.boto3.client")
    def test_creates_client(self, mock_client: MagicMock) -> None:
        """Test that EC2 client is created."""
        mock_client.return_value = MagicMock()
        result = create_ec2_client("us-east-1")
        assert result is not None

    @patch("orfmi.ec2.boto3.client")
    def test_passes_region(self, mock_client: MagicMock) -> None:
        """Test that region is passed to boto3.client."""
        create_ec2_client("us-west-2")
        assert mock_client.call_args.kwargs["region_name"] == "us-west-2"


@pytest.mark.unit
class TestIsCapacityError:
    """Tests for is_capacity_error function."""

    def test_returns_true_for_capacity_error(self) -> None:
        """Test that True is returned for capacity error codes."""
        errors = [{"ErrorCode": "InsufficientInstanceCapacity"}]
        assert is_capacity_error(errors) is True

    def test_returns_true_for_spot_limit_error(self) -> None:
        """Test that True is returned for spot limit error."""
        errors = [{"ErrorCode": "MaxSpotInstanceCountExceeded"}]
        assert is_capacity_error(errors) is True

    def test_returns_false_for_other_error(self) -> None:
        """Test that False is returned for non-capacity errors."""
        errors = [{"ErrorCode": "InvalidParameterValue"}]
        assert is_capacity_error(errors) is False

    def test_returns_false_for_empty_list(self) -> None:
        """Test that False is returned for empty error list."""
        assert is_capacity_error([]) is False

    def test_returns_true_when_mixed_errors(self) -> None:
        """Test that True is returned when any error is capacity-related."""
        errors = [
            {"ErrorCode": "InvalidParameterValue"},
            {"ErrorCode": "InsufficientCapacity"},
        ]
        assert is_capacity_error(errors) is True


@pytest.mark.unit
class TestCheckInstanceState:
    """Tests for check_instance_state function."""

    def test_no_error_when_running(self) -> None:
        """Test that no error is raised when instance is running."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"State": {"Name": "running"}}]}]
        }
        check_instance_state(ec2, "i-12345")
        assert ec2.describe_instances.call_count == 1

    def test_raises_when_terminated(self) -> None:
        """Test that InstanceTerminatedError is raised when terminated."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "State": {"Name": "terminated"},
                    "StateReason": {"Message": "User initiated"},
                }]
            }]
        }
        with pytest.raises(InstanceTerminatedError, match="terminated"):
            check_instance_state(ec2, "i-12345")

    def test_raises_when_stopped(self) -> None:
        """Test that InstanceTerminatedError is raised when stopped."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "State": {"Name": "stopped"},
                    "StateReason": {"Message": "Spot interrupted"},
                }]
            }]
        }
        with pytest.raises(InstanceTerminatedError, match="stopped"):
            check_instance_state(ec2, "i-12345")

    def test_includes_reason_in_error(self) -> None:
        """Test that state reason is included in error message."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "State": {"Name": "shutting-down"},
                    "StateReason": {"Message": "Client.SpotInstanceTermination"},
                }]
            }]
        }
        with pytest.raises(InstanceTerminatedError, match="SpotInstanceTermination"):
            check_instance_state(ec2, "i-12345")

    def test_handles_missing_state_reason(self) -> None:
        """Test that missing StateReason is handled."""
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{"State": {"Name": "terminated"}}]
            }]
        }
        with pytest.raises(InstanceTerminatedError, match="Unknown"):
            check_instance_state(ec2, "i-12345")


@pytest.mark.unit
class TestCreateFleetInstancePurchaseType:
    """Tests for create_fleet_instance with purchase_type."""

    def test_spot_purchase_type_uses_spot_options(
        self, fleet_ec2_mock: MagicMock
    ) -> None:
        """Test that spot purchase type uses SpotOptions."""
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
            purchase_type="spot",
        )
        create_fleet_instance(fleet_ec2_mock, "test-template", config)
        call_kwargs = fleet_ec2_mock.create_fleet.call_args.kwargs
        assert "SpotOptions" in call_kwargs

    def test_on_demand_purchase_type_uses_on_demand_options(
        self, fleet_ec2_mock: MagicMock
    ) -> None:
        """Test that on-demand purchase type uses OnDemandOptions."""
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
            purchase_type="on-demand",
        )
        create_fleet_instance(fleet_ec2_mock, "test-template", config)
        call_kwargs = fleet_ec2_mock.create_fleet.call_args.kwargs
        assert "OnDemandOptions" in call_kwargs

    def test_raises_capacity_error_on_capacity_failure(
        self, fleet_ec2_mock: MagicMock
    ) -> None:
        """Test that CapacityError is raised for capacity failures."""
        fleet_ec2_mock.create_fleet.return_value = {
            "Instances": [],
            "Errors": [{"ErrorCode": "InsufficientInstanceCapacity"}],
        }
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
        )
        with pytest.raises(CapacityError, match="Capacity error"):
            create_fleet_instance(fleet_ec2_mock, "test-template", config)

    def test_raises_runtime_error_on_other_failure(
        self, fleet_ec2_mock: MagicMock
    ) -> None:
        """Test that RuntimeError is raised for non-capacity failures."""
        fleet_ec2_mock.create_fleet.return_value = {
            "Instances": [],
            "Errors": [{"ErrorCode": "InvalidParameterValue"}],
        }
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
        )
        with pytest.raises(RuntimeError, match="Failed to create fleet"):
            create_fleet_instance(fleet_ec2_mock, "test-template", config)

    def test_sets_correct_target_capacity_type(
        self, fleet_ec2_mock: MagicMock
    ) -> None:
        """Test that DefaultTargetCapacityType is set correctly."""
        config = FleetConfig(
            instance_types=["t3.micro"],
            subnet_ids=["subnet-12345"],
            purchase_type="spot",
        )
        create_fleet_instance(fleet_ec2_mock, "test-template", config)
        call_kwargs = fleet_ec2_mock.create_fleet.call_args.kwargs
        target_spec = call_kwargs["TargetCapacitySpecification"]
        assert target_spec["DefaultTargetCapacityType"] == "spot"

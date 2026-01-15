# ORFMI - Open Rainforest Machine Image

A Python CLI tool for creating AWS AMIs from configuration files and
setup scripts.

## Installation

```bash
pip install orfmi
```

## Usage

### Using a Configuration File

```bash
orfmi --config-file config.yml --setup-file setup.sh
```

### Using CLI Flags

```bash
orfmi --ami-name my-ami \
      --region us-east-1 \
      --source-ami "debian-12-*" \
      --subnet-ids subnet-12345 subnet-67890 \
      --instance-types t3.micro t3.small \
      --setup-file setup.sh
```

### Arguments

#### Required (one of)

Either use `--config-file` OR provide all individual flags:

- `--config-file FILE` - Path to the YAML configuration file
- `--ami-name NAME` - Name for the created AMI
- `--region REGION` - AWS region
- `--source-ami AMI_ID` - Source AMI name pattern
- `--subnet-ids SUBNET [SUBNET ...]` - Subnet IDs for instance launch
- `--instance-types TYPE [TYPE ...]` - Instance types to try

#### Always Required

- `--setup-file FILE` - Path to the setup script (bash or PowerShell)

#### Optional

- `--purchase-type TYPE` - Instance purchase type: `on-demand` or `spot` (default: `on-demand`)
- `--max-retries N` - Maximum retries on capacity errors (default: 3)
- `--extra-files FILE [FILE ...]` - Additional files to upload
- `-v, --verbose` - Enable verbose output
- `-q, --quiet` - Suppress output except for errors and the final AMI ID

## Configuration File

The configuration file is a YAML file with the following structure:

```yaml
# Required fields
ami_name: my-custom-ami
region: us-east-1
source_ami: debian-12-*  # AMI name pattern to search for
subnet_ids:
  - subnet-12345abc
  - subnet-67890def
instance_types:
  - t3.micro
  - t3.small

# Optional fields
ami_description: My custom AMI for production
iam_instance_profile: my-instance-profile
purchase_type: on-demand  # on-demand or spot, default: on-demand
max_retries: 3            # default: 3 retries on capacity errors
ssh_username: admin       # default: admin
ssh_timeout: 300          # default: 300 seconds
ssh_retries: 30           # default: 30 retries
platform: linux           # linux or windows, default: linux
tags:
  Name: my-ami
  Environment: production
```

### Required Fields

| Field           | Description                                       |
| --------------- | ------------------------------------------------- |
| `ami_name`      | Name for the created AMI                          |
| `region`        | AWS region                                        |
| `source_ami`    | Source AMI name pattern (supports wildcards)      |
| `subnet_ids`    | List of subnet IDs for launching the instance     |
| `instance_types`| List of instance types to try (uses EC2 Fleet)    |

### Optional Fields

| Field                  | Default     | Description                            |
| ---------------------- | ----------- | -------------------------------------- |
| `ami_description`      | `""`        | Description for the AMI                |
| `iam_instance_profile` | `null`      | IAM instance profile name              |
| `purchase_type`        | `on-demand` | Purchase type (`on-demand` or `spot`)  |
| `max_retries`          | `3`         | Max retries on capacity errors         |
| `ssh_username`         | `admin`     | SSH username for connecting            |
| `ssh_timeout`          | `300`       | SSH command timeout in seconds         |
| `ssh_retries`          | `30`        | Number of SSH connection retries       |
| `platform`             | `linux`     | Platform type (`linux`/`windows`)      |
| `tags`                 | `{}`        | Tags to apply to resources             |

## Setup Script

The setup script runs on the instance to configure it before creating
the AMI.

### Linux (Bash)

```bash
#!/bin/bash
set -e

# Update packages
apt-get update
apt-get upgrade -y

# Install required software
apt-get install -y docker.io git

# Enable services
systemctl enable docker

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*
```

### Windows (PowerShell)

```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
$url = 'https://chocolatey.org/install.ps1'
iex ((New-Object System.Net.WebClient).DownloadString($url))

# Install software
choco install -y git docker-desktop
```

## Exit Codes

| Code | Description                   |
| ---- | ----------------------------- |
| 0    | Success - AMI created         |
| 1    | Build failure                 |
| 2    | Configuration or usage error  |

## Output

On success, the tool outputs the AMI ID in the format:

```text
AMI_ID=ami-0123456789abcdef0
```

## How It Works

1. Parses the configuration file or CLI arguments
2. Looks up the source AMI by name pattern
3. Creates temporary resources (key pair, security group, launch template)
4. Launches an EC2 instance using EC2 Fleet (on-demand or spot)
5. Waits for the instance to be ready
6. Connects via SSH and runs the setup script
7. Creates an AMI from the configured instance
8. Cleans up all temporary resources
9. Outputs the AMI ID

### Retry Logic

The tool automatically retries on capacity errors (e.g., insufficient
capacity, instance limit exceeded) and spot instance interruptions.
Use `--max-retries` to configure the maximum number of retry attempts.

## License

Apache License 2.0

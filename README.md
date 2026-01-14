# ORMI - Open Rainforest Machine Image

A Python CLI tool for creating AWS AMIs from configuration files and setup scripts.

## Installation

```bash
pip install ormi
```

## Usage

```bash
ormi --config-file config.yml --setup-file setup.sh
```

### Required Arguments

- `--config-file FILE` - Path to the YAML configuration file
- `--setup-file FILE` - Path to the setup script (bash for Linux, PowerShell for Windows)

### Optional Arguments

- `--extra-files FILE [FILE ...]` - Additional files to upload to the instance
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
ssh_username: admin  # default: admin
ssh_timeout: 300     # default: 300 seconds
ssh_retries: 30      # default: 30 retries
platform: linux      # linux or windows, default: linux
tags:
  Name: my-ami
  Environment: production
```

### Required Fields

| Field | Description |
|-------|-------------|
| `ami_name` | Name for the created AMI |
| `region` | AWS region |
| `source_ami` | Source AMI name pattern (supports wildcards) |
| `subnet_ids` | List of subnet IDs for launching the instance |
| `instance_types` | List of instance types to try (uses EC2 Fleet) |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `ami_description` | `""` | Description for the AMI |
| `iam_instance_profile` | `null` | IAM instance profile name |
| `ssh_username` | `admin` | SSH username for connecting |
| `ssh_timeout` | `300` | SSH command timeout in seconds |
| `ssh_retries` | `30` | Number of SSH connection retries |
| `platform` | `linux` | Platform type (`linux` or `windows`) |
| `tags` | `{}` | Tags to apply to resources |

## Setup Script

The setup script is executed on the instance to configure it before creating the AMI.

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
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install software
choco install -y git docker-desktop
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success - AMI created |
| 1 | Build failure |
| 2 | Configuration or usage error |

## Output

On success, the tool outputs the AMI ID in the format:

```
AMI_ID=ami-0123456789abcdef0
```

## How It Works

1. Parses the configuration file
2. Looks up the source AMI by name pattern
3. Creates temporary resources (key pair, security group, launch template)
4. Launches an EC2 spot instance using EC2 Fleet
5. Waits for the instance to be ready
6. Connects via SSH and runs the setup script
7. Creates an AMI from the configured instance
8. Cleans up all temporary resources
9. Outputs the AMI ID

## License

Apache License 2.0

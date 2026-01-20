terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
        source = "hashicorp/local"
        version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = "us-east-1"  # N. Virginia (Change if needed)
}

# 1. Create a Security Group
resource "aws_security_group" "philly_sg" {
  name        = "philly_sniper_sg"
  description = "Allow SSH and Streamlit"

  # SSH Access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Warning: Open to world, restrict in prod if possible
  }

  # Streamlit Dashboard
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTP/HTTPS (Standard)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound (Allow all)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. Generate SSH Key Pair
resource "tls_private_key" "pk" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "kp" {
  key_name   = "philly_sniper_key"
  public_key = tls_private_key.pk.public_key_openssh
}

# Save Private Key Locally
resource "local_file" "ssh_key" {
  filename        = "${path.module}/philly_key.pem"
  content         = tls_private_key.pk.private_key_pem
  file_permission = "0400"
}

# 3. Find latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

# 4. Create EC2 Instance
resource "aws_instance" "app_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro" # Free tier eligible
  key_name      = aws_key_pair.kp.key_name
  vpc_security_group_ids = [aws_security_group.philly_sg.id]

  tags = {
    Name = "PhillyPSniper-Server"
  }
  
  # Optional: User Data to install Docker on launch
  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y docker.io python3-pip
              sudo usermod -aG docker ubuntu
              # Install Docker Compose V2 (Standalone)
              sudo curl -L https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
              sudo chmod +x /usr/local/bin/docker-compose
              EOF
}

# 5. Output IP and Instructions
output "server_ip" {
  value = aws_instance.app_server.public_ip
}

output "ssh_command" {
  value = "ssh -i philly_key.pem ubuntu@${aws_instance.app_server.public_ip}"
}

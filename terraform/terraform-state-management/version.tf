terraform {
  # 1. Terraform CLI Version
  required_version = ">= 1.0" # Specify the minimum required version of the Terraform CLI

  # 2. Provider Requirements
  required_providers {
    aws = {
      source  = "hashicorp/aws" # The official source for the AWS provider
      version = "~> 5.0"        # Specify a version constraint (e.g., v5.x but not v6.0)
    }
  }

  # 3. State Backend (Crucial context for this directory's state)
  # Since this directory CREATES the S3 backend, its own state must be local.
  # Therefore, you should NOT define a backend block here.
}
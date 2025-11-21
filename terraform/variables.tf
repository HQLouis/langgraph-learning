variable "aws_region" {
  type        = string
  description = "AWS region to create resources in"
  default     = "eu-central-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, staging, prod)"
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Project name"
  default     = "conversational-ai"
}

variable "s3_prompts_bucket" {
  type = string
  description = "Name of the S3 bucket to store prompts"
  default = "conversational-ai-prompts-bucket"
}
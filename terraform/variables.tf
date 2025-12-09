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
  type        = string
  description = "Name of the S3 bucket to store prompts"
  default     = "conversational-ai-prompts-bucket"
}

variable "api_subdomain" {
  type        = string
  description = "Subdomain for the API"
  default     = "api"
}

variable "prompt_admin_subdomain" {
  type        = string
  description = "Subdomain for the Prompt Admin UI"
  default     = "admin"
}

variable "web_client_subdomain" {
  type        = string
  description = "Subdomain for the Web Client UI"
  default     = "app"
}

variable "domain_name" {
  type        = string
  description = "Root domain name for the application"
  default     = "lingolino.io"
}

variable "ecs_task_memory" {
  type        = string
  description = "Memory allocated to the ECS task (in MiB)"
  default     = "512"
}

variable "ecs_task_cpu" {
  type        = string
  description = "CPU units allocated to the ECS task"
  default     = "256"
}

variable "ecs_desired_count" {
  type        = number
  description = "Desired number of ECS task instances"
  default     = 1
}

variable "ecs_min_capacity" {
  type        = number
  description = "Minimum capacity for ECS service auto-scaling"
  default     = 1
}

variable "ecs_max_capacity" {
  type        = number
  description = "Maximum capacity for ECS service auto-scaling"
  default     = 3
}
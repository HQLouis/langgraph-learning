# ============================================================================
# Terraform Configuration for Lingolino Infrastructure
# ============================================================================
#
# This is the main entry point for the Terraform configuration.
# The infrastructure has been organized into logical files for better
# maintainability and readability:
#
# 01-versions.tf         - Terraform and provider configurations
# 02-data-sources.tf     - Data sources for lookups
# 03-networking.tf       - VPC, subnets, route tables
# 04-security-groups.tf  - Security groups for ALB and ECS
# 05-alb.tf              - Application Load Balancer and listeners
# 06-ecr.tf              - ECR repository for Docker images
# 07-iam.tf              - IAM roles and policies for ECS
# 08-ecs-cluster.tf      - ECS cluster configuration
# 09-s3-frontend.tf      - S3 buckets for frontend hosting
# 10-cloudfront.tf       - CloudFront distributions
# 11-route53-acm.tf      - Route53 records and ACM certificates
# 12-cloudwatch.tf       - CloudWatch logs and monitoring
# ecs.tf                 - ECS service and task definitions
# variables.tf           - Input variables
# outputs.tf             - Output values
#
# Note: Terraform automatically loads all *.tf files in the directory,
# so there are no module calls needed here.
# ============================================================================


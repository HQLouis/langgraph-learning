# ============================================================================
# Outputs for Lingolino Infrastructure
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer (for Route53)"
  value       = aws_lb.main.zone_id
}

output "alb_url" {
  description = "Full URL of the Application Load Balancer"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.api.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "web_client_bucket" {
  description = "S3 bucket name for web client"
  value       = aws_s3_bucket.web_client.id
}

output "web_client_website_endpoint" {
  description = "S3 website endpoint for web client"
  value       = aws_s3_bucket_website_configuration.web_client.website_endpoint
}

output "web_client_cloudfront_url" {
  description = "CloudFront distribution URL for web client"
  value       = "https://${aws_cloudfront_distribution.web_client.domain_name}"
}

output "web_client_cloudfront_id" {
  description = "CloudFront distribution ID for web client"
  value       = aws_cloudfront_distribution.web_client.id
}

output "prompt_admin_bucket" {
  description = "S3 bucket name for prompt admin UI"
  value       = aws_s3_bucket.prompt_admin.id
}

output "prompt_admin_website_endpoint" {
  description = "S3 website endpoint for prompt admin UI"
  value       = aws_s3_bucket_website_configuration.prompt_admin.website_endpoint
}

output "prompt_admin_cloudfront_url" {
  description = "CloudFront distribution URL for prompt admin UI"
  value       = "https://${aws_cloudfront_distribution.prompt_admin.domain_name}"
}

output "prompt_admin_cloudfront_id" {
  description = "CloudFront distribution ID for prompt admin UI"
  value       = aws_cloudfront_distribution.prompt_admin.id
}

output "ecs_task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN of ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

output "security_group_alb" {
  description = "Security group ID for ALB"
  value       = aws_security_group.alb.id
}

output "security_group_ecs_tasks" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}

# ============================================================================
# Next Steps Output
# ============================================================================

output "next_steps" {
  description = "Next steps for deployment"
  value       = <<-EOT

    ✅ Infrastructure Created Successfully!

    📋 Next Steps:

    1. Configure Route53 DNS:
       - Point ${var.web_client_subdomain}.${var.domain_name} to ${aws_cloudfront_distribution.web_client.domain_name}
       - Point ${var.prompt_admin_subdomain}.${var.domain_name} to ${aws_cloudfront_distribution.prompt_admin.domain_name}
       - Point ${var.api_subdomain}.${var.domain_name} to ${aws_lb.main.dns_name}

    2. Create Secrets in AWS Secrets Manager:
       aws secretsmanager create-secret \
         --name lingolino/google-api-key \
         --secret-string "YOUR_GOOGLE_API_KEY" \
         --region ${var.aws_region}

    3. Update GitHub Secrets:
       - AWS_ACCOUNT_ID: ${data.aws_caller_identity.current.account_id}
       - AWS_REGION: ${var.aws_region}
       - ECR_REPOSITORY: ${aws_ecr_repository.api.name}
       - ECS_CLUSTER: ${aws_ecs_cluster.main.name}
       - WEB_CLIENT_BUCKET: ${aws_s3_bucket.web_client.id}
       - WEB_CLIENT_CLOUDFRONT_ID: ${aws_cloudfront_distribution.web_client.id}
       - PROMPT_ADMIN_BUCKET: ${aws_s3_bucket.prompt_admin.id}
       - PROMPT_ADMIN_CLOUDFRONT_ID: ${aws_cloudfront_distribution.prompt_admin.id}

    4. Access URLs:
       - API (ALB): ${aws_lb.main.dns_name}
       - Web Client: ${aws_cloudfront_distribution.web_client.domain_name}
       - Prompt Admin: ${aws_cloudfront_distribution.prompt_admin.domain_name}

    5. Deploy using GitHub Actions:
       - Push to main branch to trigger deployment

    📖 See DEPLOYMENT.md for detailed instructions
  EOT
}

# ============================================================================
# Prompt Repository Outputs
# ============================================================================
output "prompt_repository_bucket" {
  description = "S3 bucket name for prompt repository"
  value       = aws_s3_bucket.prompt_repository.id
}
output "prompt_repository_arn" {
  description = "ARN of the prompt repository bucket"
  value       = aws_s3_bucket.prompt_repository.arn
}
output "prompt_repository_url" {
  description = "URL for accessing prompts in the repository"
  value       = "https://${aws_s3_bucket.prompt_repository.bucket_regional_domain_name}"
}
output "prompt_repository_s3_url" {
  description = "S3 URL for prompt repository (for ECS tasks)"
  value       = "s3://${aws_s3_bucket.prompt_repository.id}"
}

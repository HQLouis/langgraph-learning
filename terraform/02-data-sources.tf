# ============================================================================
# Data Sources
# ============================================================================

# Get current AWS account information
data "aws_caller_identity" "current" {}

# Get available availability zones in the region
data "aws_availability_zones" "available" {
  state = "available"
}

# Get Route53 hosted zone for domain
data "aws_route53_zone" "lingolino" {
  name         = "lingolino.io."
  private_zone = false
}


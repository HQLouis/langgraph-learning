# ============================================================================
# ACM Certificate for CloudFront (must be in us-east-1)
# ============================================================================

resource "aws_acm_certificate" "lingolino" {
  provider          = aws.us_east_1
  domain_name       = "*.lingolino.io"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================================
# Route53 Records for Certificate Validation
# ============================================================================

resource "aws_route53_record" "lingolino_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.lingolino.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.lingolino.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "lingolino" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.lingolino.arn
  validation_record_fqdns = [for record in aws_route53_record.lingolino_cert_validation : record.fqdn]
}

# ============================================================================
# Route53 A Records for CloudFront Distributions
# ============================================================================

resource "aws_route53_record" "web_client_alias" {
  zone_id = data.aws_route53_zone.lingolino.zone_id
  name    = "https://${var.web_client_subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web_client.domain_name
    zone_id                = aws_cloudfront_distribution.web_client.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "prompt_admin_alias" {
  zone_id = data.aws_route53_zone.lingolino.zone_id
  name    = "https://${var.prompt_admin_subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.prompt_admin.domain_name
    zone_id                = aws_cloudfront_distribution.prompt_admin.hosted_zone_id
    evaluate_target_health = false
  }
}


# ============================================================================
# CloudFront Origin Access Identities
# ============================================================================

resource "aws_cloudfront_origin_access_identity" "web_client" {
  comment = "OAI for text-chat-client.lingolino.io"
}

resource "aws_cloudfront_origin_access_identity" "prompt_admin" {
  comment = "OAI for prompt-admin.lingolino.io"
}

# ============================================================================
# Web Client CloudFront Distribution
# ============================================================================

resource "aws_cloudfront_distribution" "web_client" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Lingolino Web Client"
  default_root_object = "index.html"
  aliases             = ["text-chat-client.lingolino.io"]

  origin {
    domain_name = aws_s3_bucket.web_client.bucket_regional_domain_name
    origin_id   = "S3-web-client"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.web_client.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-web-client"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.lingolino.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name = "Lingolino Web Client CDN"
  }

  # Make sure cert is issued before CloudFront is created
  depends_on = [aws_acm_certificate_validation.lingolino]
}

# ============================================================================
# Prompt Admin CloudFront Distribution
# ============================================================================

resource "aws_cloudfront_distribution" "prompt_admin" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Lingolino Prompt Admin UI"
  default_root_object = "index.html"
  aliases             = ["prompt-admin.lingolino.io"]

  origin {
    domain_name = aws_s3_bucket.prompt_admin.bucket_regional_domain_name
    origin_id   = "S3-prompt-admin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.prompt_admin.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-prompt-admin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.lingolino.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name = "Lingolino Prompt Admin CDN"
  }

  depends_on = [aws_acm_certificate_validation.lingolino]
}


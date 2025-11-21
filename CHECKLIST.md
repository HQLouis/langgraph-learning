# ✅ AWS Deployment Checklist

Use this checklist to ensure a successful deployment of Lingolino to AWS.

---

## 📋 Phase 1: Prerequisites (15 minutes)

### Install Required Tools
- [ ] Install Terraform: `brew install terraform`
- [ ] Verify Terraform: `terraform --version` (should be >= 1.0)
- [ ] Install AWS CLI: `brew install awscli`
- [ ] Verify AWS CLI: `aws --version` (should be >= 2.0)
- [ ] Verify Docker: `docker --version`

### AWS Account Setup
- [ ] AWS account created or accessible
- [ ] Root account has MFA enabled (security best practice)
- [ ] Billing alerts configured (optional but recommended)

### Create IAM User for Deployments
- [ ] Created IAM user: `github-actions-lingolino`
- [ ] Attached policy: `AmazonEC2ContainerRegistryFullAccess`
- [ ] Attached policy: `AmazonECS_FullAccess`
- [ ] Attached policy: `AmazonS3FullAccess`
- [ ] Attached policy: `CloudFrontFullAccess`
- [ ] Attached policy: `ElasticLoadBalancingFullAccess`
- [ ] Created custom policy: `LingolinoSecretsManagerAccess`
- [ ] Generated access key
- [ ] Saved access key ID securely
- [ ] Saved secret access key securely

**📖 Guide**: [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md)

### Configure AWS CLI Locally
- [ ] Ran: `aws configure`
- [ ] Entered AWS access key ID
- [ ] Entered AWS secret access key
- [ ] Set region: `eu-central-1`
- [ ] Set output format: `json`
- [ ] Verified: `aws sts get-caller-identity` (shows your account)

---

## 📋 Phase 2: Infrastructure Deployment (20 minutes)

### Prepare Environment
- [ ] Cloned repository locally
- [ ] Navigated to project root
- [ ] Created `.env` file from `.env.example`
- [ ] Added `GOOGLE_API_KEY` to `.env`

### Deploy with Terraform
- [ ] Ran: `./deploy.sh init` (initializes Terraform)
- [ ] Ran: `./deploy.sh plan` (reviews changes)
- [ ] Ran: `./deploy.sh deploy` (deploys infrastructure)
- [ ] Deployment completed without errors
- [ ] Saved output values (ALB URL, ECR URL, etc.)

**Or manual steps**:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Verify Infrastructure
- [ ] VPC created
- [ ] ECS cluster created: `lingolino-cluster-dev`
- [ ] ECR repository created: `lingolino-api`
- [ ] ALB created and running
- [ ] S3 buckets created (2 buckets)
- [ ] CloudFront distributions created (2 distributions)
- [ ] Security groups configured
- [ ] IAM roles created

**Check in AWS Console**:
- ECS → Clusters → `lingolino-cluster-dev`
- ECR → Repositories → `lingolino-api`
- EC2 → Load Balancers → `lingolino-alb-dev`
- S3 → Buckets (see 2 new buckets)
- CloudFront → Distributions (see 2 new distributions)

---

## 📋 Phase 3: Secrets & Configuration (5 minutes)

### Create AWS Secrets
- [ ] Ran secret creation command:
```bash
aws secretsmanager create-secret \
  --name lingolino/google-api-key \
  --secret-string "YOUR_GOOGLE_API_KEY" \
  --region eu-central-1
```
- [ ] Verified secret: `aws secretsmanager describe-secret --secret-id lingolino/google-api-key`

### Configure GitHub Repository
- [ ] Went to GitHub → Your Repo → Settings → Secrets → Actions
- [ ] Added secret: `AWS_ACCESS_KEY_ID` = `AKIA...`
- [ ] Added secret: `AWS_SECRET_ACCESS_KEY` = `wJalr...`
- [ ] Verified both secrets show as configured

---

## 📋 Phase 4: Initial Image Push (10 minutes)

### Login to ECR
- [ ] Ran: `./deploy.sh image` (shows commands)
- [ ] Copied ECR login command
- [ ] Logged into ECR successfully

**Or manual**:
```bash
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-central-1.amazonaws.com
```

### Build and Push Docker Image
- [ ] Built image: `docker build -t lingolino-api .`
- [ ] Tagged image with ECR URL
- [ ] Pushed image to ECR
- [ ] Verified image in ECR console

**Full commands**:
```bash
docker build -t lingolino-api .
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url)
docker tag lingolino-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Verify Image
- [ ] Checked ECR console for image
- [ ] Image has tag `latest`
- [ ] Image scan completed (if enabled)

---

## 📋 Phase 5: First Deployment (10 minutes)

### Commit Deployment Files
- [ ] Staged files: `git add .`
- [ ] Committed: `git commit -m "Add AWS deployment pipeline"`
- [ ] Pushed: `git push origin main`

### Monitor GitHub Actions
- [ ] Went to GitHub → Your Repo → Actions
- [ ] Watched "Deploy Backend API to AWS Fargate" workflow
- [ ] Watched "Deploy Frontend to S3 & CloudFront" workflow
- [ ] Both workflows completed with green checkmarks ✅

### Verify Deployment
- [ ] Backend workflow deployed successfully
- [ ] Frontend workflow deployed successfully
- [ ] No errors in workflow logs

---

## 📋 Phase 6: Verification (10 minutes)

### Test API Backend
- [ ] Got ALB URL: `terraform -chdir=terraform output alb_url`
- [ ] Tested health: `curl http://[ALB-URL]/health`
- [ ] Response: `{"status":"healthy"}`
- [ ] Tested docs: Opened `http://[ALB-URL]/docs` in browser
- [ ] API documentation loads correctly

### Test Web Client
- [ ] Got CloudFront URL: `terraform -chdir=terraform output web_client_cloudfront_url`
- [ ] Opened URL in browser
- [ ] Web client loads
- [ ] Can start conversation
- [ ] Can send messages
- [ ] Receives responses from API

### Test Prompt Admin UI
- [ ] Got CloudFront URL: `terraform -chdir=terraform output prompt_admin_cloudfront_url`
- [ ] Opened URL in browser
- [ ] Admin UI loads
- [ ] Can load prompts from S3
- [ ] Can save prompts to S3 (if write access configured)

### Check Logs
- [ ] Ran: `aws logs tail /ecs/lingolino-api --since 5m`
- [ ] Logs show application starting
- [ ] No critical errors in logs

### Check ECS Service
- [ ] Ran: `aws ecs describe-services --cluster lingolino-cluster-dev --services lingolino-api-service`
- [ ] Service status: `ACTIVE`
- [ ] Running count: `1`
- [ ] Desired count: `1`

---

## 📋 Phase 7: Optional - Custom Domain (30 minutes)

### Request SSL Certificate
- [ ] Requested ACM certificate for `*.lingolino.io` in `us-east-1`
- [ ] Noted certificate ARN
- [ ] Added DNS validation records to domain registrar
- [ ] Waited for certificate validation (5-30 minutes)
- [ ] Certificate status: `Issued`

### Configure Route53 (or DNS Provider)
- [ ] Created Route53 hosted zone for `lingolino.io` (if not exists)
- [ ] Noted nameservers
- [ ] Updated domain registrar with Route53 nameservers
- [ ] Created A record: `api.lingolino.io` → ALB
- [ ] Created CNAME: `text-chat-client.lingolino.io` → CloudFront
- [ ] Created CNAME: `prompt-admin.lingolino.io` → CloudFront

### Update Terraform with Certificate
- [ ] Edited `terraform/variables.tf` - uncommented certificate ARN variable
- [ ] Added certificate ARN value
- [ ] Edited `terraform/main.tf` - uncommented HTTPS listeners
- [ ] Ran: `terraform apply`
- [ ] HTTPS listeners created
- [ ] HTTP redirects to HTTPS

### Verify Custom Domains
- [ ] `https://api.lingolino.io/health` works
- [ ] `https://text-chat-client.lingolino.io` works
- [ ] `https://prompt-admin.lingolino.io` works
- [ ] SSL certificates valid (no browser warnings)

---

## 📋 Phase 8: Post-Deployment

### Documentation
- [ ] Saved ALB URL for reference
- [ ] Saved CloudFront URLs for reference
- [ ] Documented any custom configurations
- [ ] Shared access URLs with team

### Monitoring Setup
- [ ] Reviewed CloudWatch dashboard
- [ ] Set up CloudWatch alarms (optional)
- [ ] Configured SNS for alerts (optional)

### Cost Monitoring
- [ ] Enabled AWS Cost Explorer
- [ ] Set up budget alerts
- [ ] Tagged resources for cost tracking

### Security Review
- [ ] Reviewed IAM policies
- [ ] Reviewed security group rules
- [ ] Verified secrets are not in Git
- [ ] Enabled MFA on AWS account
- [ ] Set up CloudTrail (optional)

---

## ✅ Success Criteria

Your deployment is successful if:

✅ **Infrastructure**
- [ ] All Terraform resources created without errors
- [ ] No drift in Terraform state

✅ **Application**
- [ ] API health check returns 200 OK
- [ ] API docs accessible at `/docs`
- [ ] Web client loads and connects to API
- [ ] Can create conversation and send messages
- [ ] Receives AI responses

✅ **CI/CD**
- [ ] GitHub Actions workflows run successfully
- [ ] Backend deploys automatically on code changes
- [ ] Frontend deploys automatically on HTML changes

✅ **Monitoring**
- [ ] CloudWatch logs show application running
- [ ] No critical errors in logs
- [ ] ECS service healthy and stable

✅ **Performance**
- [ ] API response time < 2 seconds
- [ ] Streaming works smoothly
- [ ] Auto-scaling configured correctly

---

## 🎯 Quick Verification Commands

```bash
# Check AWS identity
aws sts get-caller-identity

# Check infrastructure
cd terraform && terraform output

# Check ECS service
aws ecs describe-services \
  --cluster lingolino-cluster-dev \
  --services lingolino-api-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'

# Check API health
curl $(terraform -chdir=terraform output -raw alb_url)/health

# View logs
aws logs tail /ecs/lingolino-api --follow --since 5m

# Check image in ECR
aws ecr describe-images \
  --repository-name lingolino-api \
  --query 'imageDetails[0].{Tags:imageTags,Pushed:imagePushedAt}'
```

---

## 🐛 Common Issues Checklist

If something doesn't work, check:

### Infrastructure Issues
- [ ] AWS credentials configured correctly
- [ ] Terraform state not corrupted
- [ ] All required AWS service quotas available
- [ ] Region is `eu-central-1` (or your chosen region)

### ECS Task Issues
- [ ] Secret exists in Secrets Manager
- [ ] IAM roles have correct permissions
- [ ] Security groups allow traffic
- [ ] Image exists in ECR

### GitHub Actions Issues
- [ ] GitHub secrets configured correctly
- [ ] IAM user has required permissions
- [ ] Workflow files have no syntax errors
- [ ] Branch is `main` (not `master`)

### Application Issues
- [ ] Environment variables set correctly in task definition
- [ ] Google API key is valid
- [ ] CORS origins include CloudFront URLs
- [ ] Health check endpoint works

### Frontend Issues
- [ ] S3 buckets have correct permissions
- [ ] CloudFront distributions deployed
- [ ] API URL updated in HTML files
- [ ] Cache invalidated after changes

---

## 📞 Support Resources

- **AWS Console**: https://console.aws.amazon.com/
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Quick Reference**: [QUICK_DEPLOY.md](QUICK_DEPLOY.md)
- **Credentials Setup**: [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md)
- **Terraform Docs**: [terraform/README.md](terraform/README.md)
- **Summary**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

---

## 🎉 Congratulations!

If you've checked all items above, your Lingolino application is successfully deployed to AWS! 🚀

**What's Next?**
- Make code changes and watch them deploy automatically
- Monitor performance in CloudWatch
- Scale as needed by updating Terraform variables
- Set up custom domain for production use

---

**Last Updated**: Ready for deployment
**Estimated Total Time**: ~70 minutes (first time)
**Subsequent Deploys**: Automatic via Git push


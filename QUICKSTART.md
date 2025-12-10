# 🚀 Quick Start - Deploy to AWS in 40 Minutes

Follow these steps to deploy Lingolino to AWS.

---

## Step 1: Install Tools (5 min)

```bash
# Install Terraform
brew install terraform

# Install AWS CLI
brew install awscli

# Verify
terraform --version
aws --version
```

---

## Step 2: Configure AWS (5 min)

```bash
# Configure AWS CLI with your credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: [Your Key]
# AWS Secret Access Key: [Your Secret]
# Default region: eu-central-1
# Default output format: json

# Test
aws sts get-caller-identity
```

**Need credentials?** See [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md)

---

## Step 3: Deploy Infrastructure (20 min)

```bash
# From project root
./deploy.sh deploy

# Review the plan, then type 'yes' to confirm
```

**Save the outputs!** You'll need them.

---

## Step 4: Create Secrets (2 min)

```bash
# Create Google API key secret
aws secretsmanager create-secret \
  --name lingolino/google-api-key \
  --secret-string "YOUR_GOOGLE_API_KEY_HERE" \
  --region eu-central-1
```

---

## Step 5: Push Initial Image (5 min)

```bash
# Get ECR URL
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push
docker build -t lingolino-api .
docker tag lingolino-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

---

## Step 6: Configure GitHub (2 min)

1. Go to GitHub → Your Repo → Settings → Secrets → Actions
2. Add secret: `AWS_ACCESS_KEY_ID`
3. Add secret: `AWS_SECRET_ACCESS_KEY`

---

## Step 7: Deploy! (1 min)

```bash
git add .
git commit -m "Add AWS deployment"
git push origin main
```

Watch at: github.com/YOUR_REPO/actions

---

## Step 8: Verify (2 min)

```bash
# Test API
ALB_URL=$(terraform -chdir=terraform output -raw alb_dns_name)
curl http://$ALB_URL/health

# Should return: {"status":"healthy"}
```

---

## ✅ Done!

Your app is now live:
- **API**: `http://[alb-dns]`
- **Docs**: `http://[alb-dns]/docs`
- **Web Client**: CloudFront URL from outputs
- **Admin UI**: CloudFront URL from outputs

---

## 📚 Next Steps

- Configure custom domain (optional)
- Set up monitoring alerts
- Review costs in AWS Cost Explorer

---

## 🆘 Problems?

1. Check [CHECKLIST.md](CHECKLIST.md)
2. Read [DEPLOYMENT.md](DEPLOYMENT.md)
3. View logs: `aws logs tail /ecs/lingolino-api --follow`

---

**🎉 Enjoy your cloud-deployed Lingolino!**


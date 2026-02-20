# 🔐 AWS Credentials Setup Guide

Quick guide to set up AWS credentials for deployment.

## Step 1: Create IAM User

1. Go to AWS Console → IAM → Users → **Add User**
2. Username: `github-actions-lingolino`
3. Access type: ✅ **Programmatic access**

## Step 2: Attach Policies

Attach these managed policies:
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonECS_FullAccess`
- `AmazonS3FullAccess`
- `CloudFrontFullAccess`
- `ElasticLoadBalancingFullAccess`

## Step 3: Create Custom Policy for Secrets Manager

Create a policy with this JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:lingolino/*"
    }
  ]
}
```

Name it: `LingolinoSecretsManagerAccess` and attach to user.

## Step 4: Save Credentials

After creating the user, **copy and save securely**:
- Access Key ID: `AKIA...`
- Secret Access Key: `wJalr...`

⚠️ **You can only see the secret once!**

## Step 5: Configure AWS CLI

```bash
aws configure

# Enter:
# AWS Access Key ID: AKIA...
# AWS Secret Access Key: wJalr...
# Default region: eu-central-1
# Default output format: json
```

## Step 6: Test

```bash
aws sts get-caller-identity
```

Should show your account details.

## Step 7: Configure GitHub Secrets

Go to GitHub → Your Repo → Settings → Secrets → Actions

Add:
- `AWS_ACCESS_KEY_ID` = your access key
- `AWS_SECRET_ACCESS_KEY` = your secret key

## Security Best Practices

✅ Never commit credentials to Git  
✅ Use IAM with least privilege  
✅ Rotate credentials every 90 days  
✅ Enable MFA on root account  

## Troubleshooting

**Issue**: "Access Denied"  
**Solution**: Verify all policies are attached

**Issue**: "Invalid credentials"  
**Solution**: Run `aws configure` again

---

**Next**: See [QUICKSTART.md](QUICKSTART.md) or [DEPLOYMENT.md](DEPLOYMENT.md)


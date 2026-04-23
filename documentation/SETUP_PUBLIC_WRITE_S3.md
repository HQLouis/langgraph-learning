# Setup S3 Bucket with Public Read/Write Access

This guide shows how to configure your S3 bucket to allow **anonymous read and write access** for the prompts folder, enabling the admin UI to work without AWS credentials.

## Security Considerations

✅ **Low Risk Scenario:**
- Only the `prompts/` folder has write access
- Text files are small (minimal storage costs)
- No sensitive data in prompts
- Easy to monitor and rollback via S3 versioning

⚠️ **Important:**
- Enable S3 versioning for rollback capability
- Monitor bucket usage via CloudWatch
- Consider adding rate limiting at the application level

---

## Step 1: Create S3 Bucket

```bash
# Create bucket in eu-central-1
aws s3 mb s3://prompt-repository --region eu-central-1
```

---

## Step 2: Disable Block Public Access

By default, AWS blocks all public access. You need to disable this for your bucket:

### Via AWS Console:

1. Go to [S3 Console](https://s3.console.aws.amazon.com/)
2. Click on your bucket: `prompt-repository`
3. Go to **Permissions** tab
4. Click **Edit** under "Block public access"
5. **Uncheck** all 4 options:
   - ☐ Block all public access
   - ☐ Block public access to buckets and objects granted through new access control lists (ACLs)
   - ☐ Block public access to buckets and objects granted through any access control lists (ACLs)
   - ☐ Block public access to buckets and objects granted through new public bucket or access point policies
   - ☐ Block public and cross-account access to buckets and objects through any public bucket or access point policies
6. Click **Save changes**
7. Type `confirm` and click **Confirm**

### Via AWS CLI:

```bash
aws s3api put-public-access-block \
  --bucket prompt-repository \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

---

## Step 3: Apply Bucket Policy

The bucket policy allows:
- ✅ **Public Read** (`s3:GetObject`) - Anyone can read prompts
- ✅ **Public Write** (`s3:PutObject`) - Anyone can upload/update prompts
- ✅ **Public List** (`s3:ListBucket`) - Anyone can list prompts folder

### Via AWS Console:

1. In your bucket, go to **Permissions** tab
2. Scroll to **Bucket policy**
3. Click **Edit**
4. Paste the policy from `S3_BUCKET_POLICY.json`
5. Replace `prompt-repository` with your actual bucket name if different
6. Click **Save changes**

### Via AWS CLI:

```bash
# Apply the bucket policy
aws s3api put-bucket-policy \
  --bucket prompt-repository \
  --policy file://S3_BUCKET_POLICY.json
```

---

## Step 4: Enable Versioning (Recommended)

This allows you to rollback to previous versions if needed:

```bash
aws s3api put-bucket-versioning \
  --bucket prompt-repository \
  --versioning-configuration Status=Enabled
```

---

## Step 5: Test Public Access

### Test Read Access:

```bash
# Should work without credentials
curl https://prompt-repository.s3.eu-central-1.amazonaws.com/prompts/speech_vocabulary_worker.txt
```

### Test Write Access:

```bash
# Upload a test file (no credentials needed)
echo "Test content" > test.txt
curl -X PUT \
  -H "Content-Type: text/plain" \
  --data-binary @test.txt \
  https://prompt-repository.s3.eu-central-1.amazonaws.com/prompts/test.txt

# Verify it was uploaded
curl https://prompt-repository.s3.eu-central-1.amazonaws.com/prompts/test.txt

# Clean up
rm test.txt
```

---

## Step 6: Upload Initial Prompts

Now you can upload prompts without AWS credentials:

```bash
cd agentic-system
python upload_prompts_to_s3.py
```

**Expected output:**
```
✓ Successfully uploaded speech_vocabulary_worker (3224 bytes)
✓ Successfully uploaded speech_grammar_worker (2780 bytes)
✓ Successfully uploaded speech_interaction_worker (2806 bytes)
✓ Successfully uploaded speech_comprehension_worker (2892 bytes)
✓ Successfully uploaded boredom_worker (2763 bytes)
✓ Successfully uploaded master_prompt (1873 bytes)
```

---

## Step 7: Configure CORS (for Web UI)

Allow the admin UI to upload from the browser:

### Via AWS Console:

1. Go to your bucket → **Permissions** tab
2. Scroll to **CORS configuration**
3. Click **Edit**
4. Paste:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag"]
  }
]
```

5. Click **Save changes**

### Via AWS CLI:

```bash
cat > cors.json << 'EOF'
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}
EOF

aws s3api put-bucket-cors \
  --bucket prompt-repository \
  --cors-configuration file://cors.json

rm cors.json
```

**For production**, restrict `AllowedOrigins` to your domain:
```json
"AllowedOrigins": ["https://yourdomain.com"]
```

---

## Monitoring & Security

### Enable CloudWatch Metrics:

```bash
# Monitor bucket requests and data transfer
aws s3api put-bucket-metrics-configuration \
  --bucket prompt-repository \
  --id EntireBucket \
  --metrics-configuration Id=EntireBucket,Filter={}
```

### Monitor Costs:

- Go to [AWS Cost Explorer](https://console.aws.amazon.com/cost-management/)
- Filter by S3 service
- Set up billing alerts

### Set Up Bucket Notifications (Optional):

Get notified when files are uploaded:

```bash
# Create SNS topic
aws sns create-topic --name prompt-uploads

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-central-1:YOUR_ACCOUNT_ID:prompt-uploads \
  --protocol email \
  --notification-endpoint your-email@example.com

# Configure bucket notifications
# (This requires additional configuration in S3 console or via CloudFormation)
```

---

## Rollback a Prompt (If Needed)

If someone uploads a bad prompt, you can rollback:

```bash
# List versions of a file
aws s3api list-object-versions \
  --bucket prompt-repository \
  --prefix prompts/speech_vocabulary_worker.txt

# Restore a previous version (copy version ID from above)
aws s3api copy-object \
  --bucket prompt-repository \
  --copy-source prompt-repository/prompts/speech_vocabulary_worker.txt?versionId=VERSION_ID \
  --key prompts/speech_vocabulary_worker.txt
```

---

## Cost Estimate

With public write access:

**Worst case scenario** (heavy abuse):
- Storage: 1 GB = $0.023/month
- PUT Requests: 10,000/month = $0.05
- GET Requests: 100,000/month = $0.04
- Data Transfer: 10 GB/month = $0.90

**Total worst case**: ~$1/month

**Realistic scenario** (normal usage):
- Storage: 100 KB = $0.00
- PUT Requests: 100/month = $0.00
- GET Requests: 1,000/month = $0.00
- Data Transfer: 100 MB/month = $0.01

**Total realistic**: Less than $0.05/month

---

## Cleanup (If Needed)

To remove public access later:

```bash
# Remove bucket policy
aws s3api delete-bucket-policy --bucket prompt-repository

# Re-enable block public access
aws s3api put-public-access-block \
  --bucket prompt-repository \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## Summary

✅ **Public Read**: Anyone can download prompts  
✅ **Public Write**: Anyone can upload/update prompts (limited to `prompts/` folder)  
✅ **No Credentials**: Upload script and admin UI work without AWS credentials  
✅ **Versioning**: Can rollback to previous versions  
✅ **Low Cost**: ~$0.01-$1/month depending on usage  
✅ **Monitoring**: CloudWatch metrics and billing alerts available  

**Your system is now ready for public prompt management!** 🚀


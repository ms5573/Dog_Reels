# Setting Up S3 Storage for Dog Reels

This guide explains how to set up AWS S3 storage for your Dog Reels application.

## 1. Create an AWS Account

If you don't already have an AWS account, sign up at [aws.amazon.com](https://aws.amazon.com/).

## 2. Create an S3 Bucket

1. Log in to the AWS Management Console
2. Navigate to S3 service
3. Click "Create bucket"
4. Choose a unique bucket name (e.g., `my-dog-reels-storage`)
5. Select a region close to your users
6. Configure bucket settings:
   - Block all public access: Uncheck if you need public access to videos
   - Enable versioning: Optional
   - Enable server-side encryption: Recommended
7. Click "Create bucket"

## 3. Set Up CORS Configuration

1. Select your bucket
2. Go to the "Permissions" tab
3. Scroll down to "Cross-origin resource sharing (CORS)"
4. Click "Edit" and add a CORS configuration:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": ["*"],  // Restrict this in production
    "ExposeHeaders": []
  }
]
```

## 4. Create an IAM User with S3 Access

1. Navigate to IAM service
2. Go to "Users" and click "Add user"
3. Choose a username (e.g., `dog-reels-app`)
4. Select "Access key - Programmatic access"
5. Click "Next: Permissions"
6. Select "Attach existing policies directly"
7. Search for and select "AmazonS3FullAccess" (Or create a more restricted policy for the specific bucket)
8. Click through to review and create the user
9. **IMPORTANT**: Save the Access Key ID and Secret Access Key shown on the final screen. You will not be able to view the Secret Access Key again.

## 5. Configure Environment Variables

Add these variables to your `.env` file:

```
USE_S3_STORAGE=true
S3_BUCKET_NAME=my-dog-reels-storage
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

## 6. Deploy with S3 Support

When deploying to a hosting service like Render.com, add these environment variables in your deployment configuration.

## 7. Test S3 Integration

1. Restart your application
2. Upload an image using the application
3. Check your S3 bucket to see if files are being uploaded properly
4. Verify that URLs in the application responses are S3 URLs

## Troubleshooting

- **Permission denied error**: Check your IAM permissions
- **Bucket not found**: Verify your bucket name and region
- **File not uploading**: Check your access keys
- **CORS error in browser**: Review your CORS configuration 
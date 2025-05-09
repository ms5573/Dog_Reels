# Deploying Dog Reels to Render.com

This guide will walk you through deploying the Dog Reels application to Render.com, a modern cloud platform for hosting web applications.

## Prerequisites

1. A Render.com account (you can sign up at [render.com](https://render.com))
2. Your code pushed to a GitHub or GitLab repository
3. AWS S3 bucket and credentials (see S3_SETUP.md)
4. API keys for OpenAI and Runway

## Deployment Options

### Option 1: Using render.yaml (Recommended)

We've included a `render.yaml` file in the repository to make deployment easier.

1. Log in to your Render account
2. Click the "Blueprint" option in the dashboard
3. Connect your GitHub/GitLab account if you haven't already
4. Select the repository containing your Dog Reels application
5. Render will detect the `render.yaml` file and suggest services to deploy
6. Review the configuration and click "Apply"
7. Fill in the required environment variables:
   - `OPENAI_API_KEY`
   - `RUNWAY_API_KEY`
   - `S3_BUCKET_NAME`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
8. Click "Create" to start the deployment

### Option 2: Manual Setup

If you prefer to set up the services manually:

#### 1. Create a Redis Service

1. From your Render dashboard, click "New" and select "Redis"
2. Name your Redis service (e.g., "dog-reels-redis")
3. Choose a region close to your users
4. Select an appropriate plan
5. Click "Create Redis"
6. Save the "Internal Connection String" for later

#### 2. Create a Web Service

1. From your Render dashboard, click "New" and select "Web Service"
2. Connect to your GitHub/GitLab repository
3. Configure the service:
   - Name: "dog-reels-web"
   - Environment: "Docker"
   - Region: Choose a region close to your users
   - Branch: Your main branch
   - Build Command: Leave empty (Docker handles this)
   - Start Command: Leave empty (Docker handles this)
4. Add the following environment variables:
   - `REDIS_URL`: Paste the internal connection string from your Redis service
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `RUNWAY_API_KEY`: Your Runway API key
   - `USE_S3_STORAGE`: "true"
   - `S3_BUCKET_NAME`: Your S3 bucket name
   - `AWS_REGION`: Your S3 bucket region
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
5. Set the Health Check Path to `/health`
6. Click "Create Web Service"

#### 3. Create a Background Worker

1. From your Render dashboard, click "New" and select "Background Worker"
2. Connect to the same GitHub/GitLab repository
3. Configure the service:
   - Name: "dog-reels-worker"
   - Environment: "Docker"
   - Region: Choose the same region as your web service
   - Branch: Your main branch
   - Build Command: Leave empty (Docker handles this)
   - Start Command: `celery -A chibi_clip.tasks worker --loglevel=info`
4. Add the same environment variables as the web service
5. Click "Create Background Worker"

## Verifying Deployment

1. Wait for all services to complete their initial deployment
2. Access your web service URL (e.g., `https://dog-reels-web.onrender.com`)
3. Test the application by uploading an image and checking if videos are generated
4. Check your S3 bucket to confirm files are being uploaded correctly

## Troubleshooting

- **Build failures**: Check the build logs for errors
- **Application errors**: Check the service logs in the Render dashboard
- **Redis connection issues**: Verify the Redis URL is correct
- **S3 storage issues**: Check AWS credentials and permissions
- **API key issues**: Verify your API keys are correct and have necessary permissions

## Scaling

To scale your application:

1. Go to the service in your Render dashboard
2. Click "Settings"
3. Under "Instances", you can increase the number of instances for more capacity
4. Consider upgrading your plan for more resources if needed

## Custom Domains

To use a custom domain:

1. Go to your web service in the Render dashboard
2. Click "Settings"
3. Under "Custom Domain", click "Add Custom Domain"
4. Follow the instructions to configure your domain 
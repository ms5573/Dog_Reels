import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';
import { createClient } from 'redis';
// @ts-ignore - cloudinary doesn't have built-in TypeScript declarations
import { v2 as cloudinary } from 'cloudinary';

// Configure Cloudinary
cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true
});

// Helper function to update status file
function updateTaskStatus(statusFile, status, stage, extraData = {}) {
  const data = {
    status: status,
    stage: stage,
    updated: new Date().toISOString(),
    ...extraData
  };
  
  fs.writeFileSync(statusFile, JSON.stringify(data));
  console.log(`Updated task status: ${status} - ${stage}`);
}

export async function POST(request: NextRequest) {
  try {
    // Create Output directory if it doesn't exist
    const outputDir = path.join(process.cwd(), 'Output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const formData = await request.formData();
    const petPhoto = formData.get('petPhoto') as File;
    const action = formData.get('action') as string;
    const email = formData.get('email') as string;

    if (!petPhoto || !action || !email) {
      return NextResponse.json(
        { error: 'Missing required fields (petPhoto, action, or email)' },
        { status: 400 }
      );
    }

    // Generate a unique task ID
    const taskId = uuidv4();
    
    // Get file buffer
    const bytes = await petPhoto.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Create a task status file to track progress
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    updateTaskStatus(statusFile, 'PENDING', 'Uploading image to cloud storage...', {
      created: new Date().toISOString(),
      userEmail: email
    });

    // Create a log file for this task
    const logFile = path.join(outputDir, `${taskId}_processing.log`);
    fs.writeFileSync(logFile, `Task ${taskId} queued for processing at ${new Date().toISOString()}\nEmail: ${email}\n`);

    try {
      // Upload image to Cloudinary
      console.log(`Uploading image to Cloudinary for task ${taskId}`);
      
      const uploadResult = await new Promise<any>((resolve, reject) => {
        cloudinary.uploader.upload_stream(
          {
            public_id: `pet_reels/${taskId}`,
            overwrite: true,
            resource_type: "image"
          },
          (error, result) => {
            if (error) reject(error);
            else resolve(result);
          }
        ).end(buffer);
      });

      const cloudinaryUrl = uploadResult?.secure_url;
      
      if (!cloudinaryUrl) {
        throw new Error('Cloudinary upload failed: No secure_url returned');
      }

      console.log(`Image uploaded to Cloudinary: ${cloudinaryUrl}`);
      fs.appendFileSync(logFile, `Image uploaded to Cloudinary: ${cloudinaryUrl}\n`);

      updateTaskStatus(statusFile, 'PENDING', 'Image uploaded, queuing for processing...', {
        cloudinary_url: cloudinaryUrl
      });

      // Connect to Redis
      const redisUrl = process.env.REDIS_URL;
      if (!redisUrl) {
        throw new Error('REDIS_URL environment variable is not set');
      }
      
      // Handle SSL certificates for Heroku Redis
      const redisConfig: any = { url: redisUrl };
      if (redisUrl.startsWith('rediss://')) {
        redisConfig.socket = {
          rejectUnauthorized: false
        };
      }
      
      const redis = createClient(redisConfig);
      await redis.connect();
      
      // Create task data with correct field names for the worker
      const taskData = {
        task_id: taskId,
        photo_url: cloudinaryUrl,  // Changed from photo_path to photo_url
        product_title: "Pet Reel",
        product_description: action,
        user_email: email,  // Changed from 'email' to 'user_email'
        created_at: new Date().toISOString()
      };
      
      // Add task to queue
      const queueName = 'pet_video_tasks';
      await redis.rPush(queueName, JSON.stringify(taskData));
      
      console.log(`Added task ${taskId} to Redis queue '${queueName}'`);
      fs.appendFileSync(logFile, `Task added to Redis queue '${queueName}'\n`);
      
      // Disconnect from Redis
      await redis.disconnect();
      
      updateTaskStatus(statusFile, 'QUEUED', 'Waiting for worker processing...', {
        queued_at: new Date().toISOString()
      });

      return NextResponse.json({
        success: true,
        task_id: taskId,
        message: 'Upload successful, processing queued. You will receive an email with the video link when ready!'
      });

    } catch (cloudinaryError) {
      console.error('Cloudinary upload error:', cloudinaryError);
      updateTaskStatus(statusFile, 'FAILED', 'Image upload failed', {
        error: cloudinaryError.message,
        completed: new Date().toISOString()
      });
      return NextResponse.json(
        { error: 'Failed to upload image to cloud storage' },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('General error in POST /api/upload:', error);
    return NextResponse.json(
      { error: 'Upload failed due to an unexpected error' },
      { status: 500 }
    );
  }
} 
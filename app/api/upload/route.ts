import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';
import { createClient } from 'redis';

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
    const dogPhoto = formData.get('dogPhoto') as File;
    const message = formData.get('message') as string;
    const email = formData.get('email') as string;

    if (!dogPhoto || !message || !email) {
      return NextResponse.json(
        { error: 'Missing required fields (dogPhoto, message, or email)' },
        { status: 400 }
      );
    }

    // Generate a unique task ID
    const taskId = uuidv4();
    
    // Get file buffer
    const bytes = await dogPhoto.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Save the image to a temporary location
    const imageExt = dogPhoto.name.split('.').pop() || 'jpg';
    const imagePath = path.join(outputDir, `${taskId}.${imageExt}`);
    fs.writeFileSync(imagePath, buffer);

    // Save message to a file
    const messagePath = path.join(outputDir, `${taskId}.txt`);
    fs.writeFileSync(messagePath, message);
    
    // Save email to a file
    const emailPath = path.join(outputDir, `${taskId}_email.txt`);
    fs.writeFileSync(emailPath, email);

    // Create a task status file to track progress
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    updateTaskStatus(statusFile, 'PENDING', 'Queued for processing...', {
      created: new Date().toISOString(),
      userEmail: email
    });

    // Create a log file for this task
    const logFile = path.join(outputDir, `${taskId}_processing.log`);
    fs.writeFileSync(logFile, `Task ${taskId} queued for processing at ${new Date().toISOString()}\nEmail: ${email}\n`);

    try {
      // Connect to Redis using environment variable
      const redisUrl = process.env.REDIS_URL;
      if (!redisUrl) {
        throw new Error('REDIS_URL environment variable is not set');
      }
      
      // Create Redis client
      const redis = createClient({ url: redisUrl });
      await redis.connect();
      
      // Create task data
      const taskData = {
        task_id: taskId,
        photo_path: imagePath,
        product_title: "Dog Birthday Video",
        product_description: message,
        email: email,
        created_at: new Date().toISOString()
      };
      
      // Add task to queue
      const queueName = 'dog_video_tasks';
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
        message: 'Upload successful, processing queued. You will receive an email with the video link.'
      });

    } catch (error) {
      console.error('Redis queue error in POST /api/upload:', error);
      if (fs.existsSync(statusFile)) {
        updateTaskStatus(statusFile, 'FAILED', 'Failed to queue task', {
          error: error.message,
          completed: new Date().toISOString()
        });
      }
      return NextResponse.json(
        { error: 'Failed to queue task for processing' },
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
import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { createClient } from 'redis';

export async function GET(request: NextRequest) {
  try {
    // Extract id from the URL
    const url = new URL(request.url);
    const id = url.pathname.split('/').pop();
    
    if (!id) {
      return NextResponse.json(
        { error: 'Task ID not provided' },
        { status: 400 }
      );
    }
    
    const taskId = id;
    const outputDir = path.join(process.cwd(), 'Output');
    
    // Check if status file exists
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    if (!fs.existsSync(statusFile)) {
      // Fall back to checking if task exists (by looking for task message file)
      const messagePath = path.join(outputDir, `${taskId}.txt`);
      if (!fs.existsSync(messagePath)) {
        return NextResponse.json(
          { error: 'Task not found' },
          { status: 404 }
        );
      }
      
      // If message file exists but no status file, create a default status
      return NextResponse.json({
        status: 'PENDING',
        stage: 'Initializing...',
        message: 'Your request is being processed'
      });
    }
    
    // Read the status file
    const statusData = fs.readFileSync(statusFile, 'utf8');
    const status = JSON.parse(statusData);
    
    // If the status is QUEUED or PROCESSING, check Redis for results
    if (status.status === 'QUEUED' || status.status === 'PROCESSING') {
      try {
        // Connect to Redis
        const redisUrl = process.env.REDIS_URL;
        if (redisUrl) {
          // Handle SSL certificates for Heroku Redis
          const redisConfig: any = { url: redisUrl };
          if (redisUrl.startsWith('rediss://')) {
            redisConfig.socket = {
              rejectUnauthorized: false
            };
          }
          
          const redis = createClient(redisConfig);
          await redis.connect();
          
          // Check for results in the results queue
          const resultQueue = 'dog_video_results';
          const queueLength = await redis.lLen(resultQueue);
          
          if (queueLength && typeof queueLength === 'number' && queueLength > 0) {
            // Check all items in the queue for our task ID
            for (let i = 0; i < queueLength; i++) {
              const result = await redis.lIndex(resultQueue, i);
              if (result) {
                try {
                  const resultData = JSON.parse(result.toString());
                  if (resultData.task_id === taskId) {
                    // Found our task result
                    if (resultData.status === 'completed' && resultData.cloudinary_video_url) {
                      // Update the status file
                      status.status = 'COMPLETE';
                      status.stage = 'Video processing complete';
                      status.result_url = resultData.cloudinary_video_url;
                      status.cloudfront_url = resultData.cloudinary_video_url;
                      status.videoPath = resultData.cloudinary_video_url;
                      status.completed = new Date().toISOString();
                      
                      // Save the updated status
                      fs.writeFileSync(statusFile, JSON.stringify(status));
                      console.log(`Updated status from Redis result: ${status.status}`);
                      
                      // Remove this result from the queue
                      await redis.lRem(resultQueue, 1, result.toString());
                    } else if (resultData.status === 'error') {
                      // Update the status file with error
                      status.status = 'FAILED';
                      status.stage = 'Processing failed';
                      status.error = resultData.error || 'Unknown error';
                      status.completed = new Date().toISOString();
                      
                      // Save the updated status
                      fs.writeFileSync(statusFile, JSON.stringify(status));
                      console.log(`Updated status with error from Redis: ${status.error}`);
                      
                      // Remove this result from the queue
                      await redis.lRem(resultQueue, 1, result.toString());
                    }
                    break;
                  }
                } catch (parseError) {
                  console.error('Error parsing Redis result:', parseError);
                }
              }
            }
          }
          
          // Disconnect from Redis
          await redis.disconnect();
        }
      } catch (redisError) {
        console.error('Redis error in status check:', redisError);
      }
    }
    
    // Extra verification for COMPLETE status
    if (status.status === 'COMPLETE' && status.videoPath) {
      // For Cloudinary URLs, we don't need to check if the file exists locally
      if (!status.videoPath.startsWith('http')) {
        // Verify that the video file actually exists locally
        if (!fs.existsSync(status.videoPath)) {
          // Video doesn't exist yet, override status to PROCESSING
          console.log(`Status claims COMPLETE but video file not found. Setting to PROCESSING.`);
          status.status = 'PROCESSING';
          status.stage = 'Finalizing your video...';
          
          // Optional: Write back the corrected status
          fs.writeFileSync(statusFile, JSON.stringify(status));
        }
      }
    }
    
    return NextResponse.json(status);
  } catch (error) {
    console.error('Status check error:', error);
    return NextResponse.json(
      { error: 'Failed to check status', status: 'FAILED' },
      { status: 500 }
    );
  }
} 
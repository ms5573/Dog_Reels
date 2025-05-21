import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

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
    
    // Extra verification for COMPLETE status
    if (status.status === 'COMPLETE') {
      // Verify that the video file actually exists
      if (status.videoPath && fs.existsSync(status.videoPath)) {
        // Video exists, we can confirm it's complete
        console.log(`Confirmed video file exists: ${status.videoPath}`);
        
        // If we don't have a CloudFront URL yet, check if we can find it in the log file
        if (!status.cloudfront_url) {
          // Look for log file with the task ID
          const logFile = path.join(outputDir, `${taskId}_processing.log`);
          
          if (fs.existsSync(logFile)) {
            try {
              const logContent = fs.readFileSync(logFile, 'utf8');
              // Look for CloudFront URL in log output
              const cloudfrontMatch = logContent.match(/https:\/\/dnznrvs05pmza\.cloudfront\.net\/[a-zA-Z0-9-]+\.mp4\?_jwt=[a-zA-Z0-9_.-]+/);
              
              if (cloudfrontMatch) {
                status.cloudfront_url = cloudfrontMatch[0];
                // Save the updated status with the CloudFront URL
                fs.writeFileSync(statusFile, JSON.stringify(status));
                console.log(`Updated status with CloudFront URL: ${status.cloudfront_url}`);
              }
            } catch (e) {
              console.error('Error reading log file:', e);
            }
          }
        }
      } else {
        // Video doesn't exist yet, override status to PROCESSING
        console.log(`Status claims COMPLETE but video file not found. Setting to PROCESSING.`);
        status.status = 'PROCESSING';
        status.stage = 'Finalizing your video...';
        
        // Optional: Write back the corrected status
        fs.writeFileSync(statusFile, JSON.stringify(status));
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
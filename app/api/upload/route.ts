import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import util from 'util';

const execPromise = util.promisify(exec);

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

    if (!dogPhoto || !message) {
      return NextResponse.json(
        { error: 'Missing required fields' },
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

    // Create a task status file to track progress
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    updateTaskStatus(statusFile, 'PENDING', 'Uploading...', {
      created: new Date().toISOString()
    });

    // Create a log file for this task
    const logFile = path.join(outputDir, `${taskId}_processing.log`);
    fs.writeFileSync(logFile, `Processing started: ${new Date().toISOString()}\n`);

    // Run the Python Chibi-Clip process asynchronously
    // Use the birthday-dance action to create a birthday themed animation
    try {
      // Update status to PROCESSING before starting the command
      updateTaskStatus(statusFile, 'PROCESSING', 'Starting image processing...');
      
      // Use conda run with the proper environment that has requests installed
      const command = `conda run -n chibi_env python chibi_clip/chibi_clip.py "${imagePath}" --action "birthday-dance" --extended-duration 45 --verbose`;
      
      console.log(`Executing command: ${command}`);
      
      // Start the async process
      const process = execPromise(command);
      
      // Set up a periodic check for process output
      const checkInterval = setInterval(async () => {
        // Check if we can determine the current stage from any output log files
        // For now, just update the status to show it's still processing
        updateTaskStatus(statusFile, 'PROCESSING', 'Creating your birthday card animation...');
      }, 10000);
      
      process
        .then(({ stdout, stderr }) => {
          // Clear the interval when the process completes
          clearInterval(checkInterval);
          
          console.log('Chibi-Clip process completed');
          console.log('Output:', stdout);
          
          // Save the output to the log file
          fs.appendFileSync(logFile, `\n--- STDOUT ---\n${stdout}\n`);
          if (stderr) {
            fs.appendFileSync(logFile, `\n--- STDERR ---\n${stderr}\n`);
          }
          
          // Look for CloudFront URL in the output
          const cloudfrontMatch = stdout.match(/https:\/\/dnznrvs05pmza\.cloudfront\.net\/[a-zA-Z0-9-]+\.mp4\?_jwt=[a-zA-Z0-9_.-]+/);
          let cloudfrontUrl = null;
          
          if (cloudfrontMatch) {
            cloudfrontUrl = cloudfrontMatch[0];
            console.log(`Found CloudFront URL: ${cloudfrontUrl}`);
          }
          
          const extendedVideoMatch = stdout.match(/Extended video with music .+? saved to: (.+\.mp4)/);
          const videoPathMatch = stdout.match(/"local_video_path": "(.+\.mp4)"/);
          
          const videoPath = extendedVideoMatch ? extendedVideoMatch[1] : 
                            videoPathMatch ? videoPathMatch[1] : null;
          
          if (videoPath && fs.existsSync(videoPath)) {
            // Update status to COMPLETE with the result URL and CloudFront URL if available
            updateTaskStatus(statusFile, 'COMPLETE', 'Your birthday card is ready!', {
              result_url: `/api/result/${taskId}`,
              videoPath: videoPath,
              cloudfront_url: cloudfrontUrl,
              completed: new Date().toISOString()
            });
          } else {
            // Update the status file with error information
            updateTaskStatus(statusFile, 'FAILED', 'Video generation failed', {
              error: 'Could not find generated video',
              completed: new Date().toISOString()
            });
          }
        })
        .catch((error) => {
          // Clear the interval when the process fails
          clearInterval(checkInterval);
          
          console.error('Error during Chibi-Clip processing:', error);
          fs.appendFileSync(logFile, `\n--- ERROR ---\n${error.message}\n${error.stack || ''}\n`);
          
          updateTaskStatus(statusFile, 'FAILED', 'Processing failed', {
            error: error.message,
            completed: new Date().toISOString()
          });
        });

      // Don't wait for the process to complete - return immediately
      return NextResponse.json({
        success: true,
        task_id: taskId,
        message: 'Upload successful, processing started'
      });
    } catch (error) {
      console.error('Execution error:', error);
      return NextResponse.json(
        { error: 'Failed to start processing' },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Upload failed' },
      { status: 500 }
    );
  }
} 
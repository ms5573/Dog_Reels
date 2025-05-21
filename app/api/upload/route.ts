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
    
    // Save email to a file (or pass as arg directly)
    const emailPath = path.join(outputDir, `${taskId}_email.txt`);
    fs.writeFileSync(emailPath, email);

    // Create a task status file to track progress
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    updateTaskStatus(statusFile, 'PENDING', 'Uploading...', {
      created: new Date().toISOString(),
      userEmail: email
    });

    // Create a log file for this task
    const logFile = path.join(outputDir, `${taskId}_processing.log`);
    fs.writeFileSync(logFile, `Processing started for task ${taskId} for email ${email}: ${new Date().toISOString()}\n`);

    // Run the Python Chibi-Clip process asynchronously
    try {
      updateTaskStatus(statusFile, 'PROCESSING', 'Starting image processing...');
      
      // IMPORTANT: Sanitize/escape inputs for command execution if they are directly used in the command string.
      // For this script, we are passing paths and a simple action string.
      // The product_title and product_description for the python script will be derived from message or a fixed value.
      // The email is now passed as a command line argument.
      const productTitle = "Dog Birthday Video";
      const productDescription = message;

      // Construct the command to run the Python script
      // Ensure paths with spaces are quoted. The email is also quoted.
      const command = `conda run -n chibi_env python product_marketing_automation.py "${imagePath}" "${productTitle}" "${productDescription}" --email "${email}" >> "${logFile}" 2>&1`;
      
      console.log(`Executing command: ${command}`);
      
      // Start the async process without awaiting its completion here
      exec(command, (error, stdout, stderr) => {
        fs.appendFileSync(logFile, `\n--- Python Script Execution Finished ---`);
        fs.appendFileSync(logFile, `\nTimestamp: ${new Date().toISOString()}`);

        if (error) {
          console.error(`Python script execution error for task ${taskId}:`, error);
          fs.appendFileSync(logFile, `\nEXECUTION ERROR: ${error.message}\n${error.stack || ''}`);
          updateTaskStatus(statusFile, 'FAILED', 'Video generation script failed', {
            error: `Script execution failed: ${error.message}`,
            completed: new Date().toISOString()
          });
          return;
        }

        let finalCloudinaryUrl = null;
        try {
            const scriptOutput = fs.readFileSync(logFile, 'utf-8');
            const cloudinaryMatch = scriptOutput.match(/Final Video URL \(Cloudinary\): (https:\/\/[^\s]+)/);
            if (cloudinaryMatch && cloudinaryMatch[1]) {
                finalCloudinaryUrl = cloudinaryMatch[1];
                console.log(`Found Cloudinary URL in script output for task ${taskId}: ${finalCloudinaryUrl}`);
            }
        } catch (readError) {
            console.error(`Error reading log file for task ${taskId} to find Cloudinary URL:`, readError);
        }

        if (finalCloudinaryUrl) {
            updateTaskStatus(statusFile, 'COMPLETE', 'Video processed and email sent!', {
                result_url: finalCloudinaryUrl,
                videoPath: finalCloudinaryUrl,
                cloudfront_url: finalCloudinaryUrl,
                completed: new Date().toISOString()
            });
        } else {
            console.warn(`Python script completed for task ${taskId}, but Cloudinary URL not found in logs.`);
            updateTaskStatus(statusFile, 'FAILED', 'Processing complete, but final video URL missing', {
                error: 'Could not retrieve final video URL after processing. Check logs.',
                completed: new Date().toISOString()
            });
        }
      });

      return NextResponse.json({
        success: true,
        task_id: taskId,
        message: 'Upload successful, processing started. You will receive an email with the video link.'
      });

    } catch (error) {
      console.error('Execution error in POST /api/upload:', error);
      if (fs.existsSync(statusFile)) {
        updateTaskStatus(statusFile, 'FAILED', 'Failed to start processing command', {
          error: error.message,
          completed: new Date().toISOString()
        });
      }
      return NextResponse.json(
        { error: 'Failed to start processing' },
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
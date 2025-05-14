import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  context: { params: { id: string } }
) {
  try {
    const taskId = context.params.id;
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
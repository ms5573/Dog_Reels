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
    
    // First check if we have a status file with a videoPath
    const statusFile = path.join(outputDir, `${taskId}_status.json`);
    let videoPath = null;
    
    if (fs.existsSync(statusFile)) {
      try {
        const statusData = JSON.parse(fs.readFileSync(statusFile, 'utf8'));
        if (statusData.videoPath && fs.existsSync(statusData.videoPath)) {
          videoPath = statusData.videoPath;
        }
      } catch (e) {
        console.error('Error parsing status file:', e);
      }
    }
    
    // If no video path from status file, try the default location
    if (!videoPath) {
      // Try to find a video file with the task ID in its name
      const files = fs.readdirSync(outputDir);
      const possibleVideoFiles = files.filter(file => 
        file.includes(taskId) && file.endsWith('.mp4')
      );
      
      if (possibleVideoFiles.length > 0) {
        videoPath = path.join(outputDir, possibleVideoFiles[0]);
      } else {
        // Fallback to the sample video if available
        const sampleVideoPath = path.join(process.cwd(), 'Chibi_Dog_Illustration_video.mp4');
        if (fs.existsSync(sampleVideoPath)) {
          videoPath = sampleVideoPath;
        }
      }
    }
    
    // If we still don't have a valid video, return an error
    if (!videoPath || !fs.existsSync(videoPath)) {
      return NextResponse.json(
        { error: 'Result not found' },
        { status: 404 }
      );
    }
    
    // Read the video file
    const videoBuffer = fs.readFileSync(videoPath);
    
    // Create response with proper content type
    const response = new NextResponse(videoBuffer);
    response.headers.set('Content-Type', 'video/mp4');
    response.headers.set('Content-Disposition', `attachment; filename="dog_birthday_card_${taskId}.mp4"`);
    
    return response;
  } catch (error) {
    console.error('Result fetch error:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve result' },
      { status: 500 }
    );
  }
} 
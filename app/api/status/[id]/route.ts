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
    
    return NextResponse.json(status);
  } catch (error) {
    console.error('Status check error:', error);
    return NextResponse.json(
      { error: 'Failed to check status', status: 'FAILED' },
      { status: 500 }
    );
  }
} 
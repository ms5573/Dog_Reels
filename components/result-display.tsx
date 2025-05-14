"use client"

import { Download, Eye, Share2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import confetti from "canvas-confetti"
import { useEffect, useRef, useState } from "react"

interface ResultDisplayProps {
  resultUrl: string
}

export default function ResultDisplay({ resultUrl }: ResultDisplayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    // Start loading the video
    if (videoRef.current) {
      videoRef.current.addEventListener('loadeddata', () => {
        setIsLoading(false);
      });
      
      // If video fails to load, handle the error
      videoRef.current.addEventListener('error', () => {
        console.error('Error loading video');
        setIsLoading(false);
      });
    }
    
    // Trigger confetti animation when component mounts
    const duration = 3 * 1000
    const animationEnd = Date.now() + duration
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 }

    function randomInRange(min: number, max: number) {
      return Math.random() * (max - min) + min
    }

    const interval: NodeJS.Timeout = setInterval(() => {
      const timeLeft = animationEnd - Date.now()

      if (timeLeft <= 0) {
        return clearInterval(interval)
      }

      const particleCount = 50 * (timeLeft / duration)

      // Since particles fall down, start a bit higher than random
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
      })
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
      })
    }, 250)

    return () => clearInterval(interval)
  }, [])

  // Function to copy the video link to clipboard
  const copyLinkToClipboard = () => {
    // Create the full URL by combining window location origin with the API path
    const fullUrl = `${window.location.origin}${resultUrl}`;
    navigator.clipboard.writeText(fullUrl)
      .then(() => {
        alert('Link copied to clipboard!');
      })
      .catch((err) => {
        console.error('Could not copy link: ', err);
      });
  };
  
  // Function to download the video
  const downloadVideo = () => {
    // Create an anchor element and simulate a click
    const a = document.createElement('a');
    a.href = resultUrl;
    a.download = 'dog-birthday-card.mp4';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="mb-6">
        <div className="inline-flex h-24 w-24 items-center justify-center rounded-full bg-green-100">
          <svg className="h-12 w-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>

      <h3 className="text-2xl font-bold text-purple-700 mb-2">Your Birthday Card is Ready!</h3>
      <p className="text-gray-600 mb-6 max-w-md">
        Your personalized dog birthday card has been created successfully. You can view it, download it, or share it with friends and family.
      </p>

      {/* Video Player */}
      <div className="w-full max-w-md mb-6 rounded-lg overflow-hidden bg-black shadow-lg">
        {isLoading && (
          <div className="w-full aspect-video flex items-center justify-center bg-gray-900">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
          </div>
        )}
        <video 
          ref={videoRef}
          controls
          autoPlay
          loop
          className={`w-full ${isLoading ? 'hidden' : 'block'}`}
          src={resultUrl}
          poster="/video-poster.jpg"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          onClick={() => window.open(resultUrl, "_blank")}
          className="bg-purple-600 hover:bg-purple-700 flex items-center gap-2"
          size="lg"
        >
          <Eye className="h-5 w-5" />
          View Fullscreen
        </Button>

        <Button 
          onClick={downloadVideo}
          className="bg-green-600 hover:bg-green-700 flex items-center gap-2" 
          size="lg"
        >
          <Download className="h-5 w-5" />
          Download Video
        </Button>
        
        <Button
          onClick={copyLinkToClipboard}
          className="bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
          size="lg"
        >
          <Share2 className="h-5 w-5" />
          Copy Link
        </Button>
      </div>
    </div>
  )
} 
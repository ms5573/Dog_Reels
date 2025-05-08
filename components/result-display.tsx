"use client"

import { Download, Eye } from "lucide-react"
import { Button } from "@/components/ui/button"
import confetti from "canvas-confetti"
import { useEffect } from "react"

interface ResultDisplayProps {
  resultUrl: string
}

export default function ResultDisplay({ resultUrl }: ResultDisplayProps) {
  useEffect(() => {
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
      <p className="text-gray-600 mb-8 max-w-md">
        Your personalized dog birthday card has been created successfully. You can view it online or download it to
        share with friends and family.
      </p>

      <div className="flex flex-col sm:flex-row gap-4">
        <Button
          onClick={() => window.open(resultUrl, "_blank")}
          className="bg-purple-600 hover:bg-purple-700 flex items-center gap-2"
          size="lg"
        >
          <Eye className="h-5 w-5" />
          View Card
        </Button>

        <Button asChild className="bg-green-600 hover:bg-green-700 flex items-center gap-2" size="lg">
          <a href={resultUrl} download="dog-birthday-card.html">
            <Download className="h-5 w-5" />
            Download Card
          </a>
        </Button>
      </div>
    </div>
  )
} 
"use client"

import { Loader2 } from "lucide-react"

interface ProcessingStatusProps {
  stage: string
}

export default function ProcessingStatus({ stage }: ProcessingStatusProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      {/* Clean loading animation */}
      <div className="relative mb-8">
        <div className="spinner"></div>
      </div>

      {/* Status text */}
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold gradient-text mb-3">
          ✨ {stage} ✨
        </h3>
        <p className="text-lg text-purple-600 font-semibold">
          🎬 Creating magic for your furry friend...
        </p>
      </div>

      {/* Description */}
      <div className="max-w-lg text-center text-gray-700 space-y-4 mb-8">
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-6 rounded-2xl border border-purple-200">
          <p className="text-lg leading-relaxed mb-3">
            🎨 We're creating a custom animated pet reel with your pet. This process may take 
            <span className="font-bold text-purple-600"> 1-3 minutes</span>.
          </p>
          <p className="text-purple-600 font-semibold">
            🔒 Please don't close this page - the magic is happening!
          </p>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="w-full max-w-md">
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-gradient-to-r from-purple-100 to-pink-100 shadow-inner">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 via-pink-500 to-yellow-500 w-1/3 rounded-full animate-pulse"></div>
        </div>
        <p className="text-center text-sm text-purple-600 mt-3 font-medium">
          🐕 Your pup is getting ready to dance! 💃
        </p>
      </div>

      {/* Fun fact */}
      <div className="mt-12 max-w-lg">
        <div className="bg-white rounded-2xl p-6 border border-purple-200 shadow-lg">
          <h4 className="text-lg font-bold text-purple-700 mb-3 text-center">
            🎭 Fun Fact While You Wait!
          </h4>
          <p className="text-gray-600 text-center leading-relaxed">
            Dogs have been our companions for over 15,000 years! 🐾 Your furry friend is about to join 
            the ranks of the most adorable animated characters ever created! 🌟
          </p>
        </div>
      </div>
    </div>
  )
} 
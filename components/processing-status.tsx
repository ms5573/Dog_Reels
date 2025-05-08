"use client"

import { Loader2 } from "lucide-react"

interface ProcessingStatusProps {
  stage: string
}

export default function ProcessingStatus({ stage }: ProcessingStatusProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-16 w-16 rounded-full border-4 border-purple-200"></div>
        </div>
        <Loader2 className="h-16 w-16 animate-spin text-purple-600" />
      </div>

      <h3 className="mt-6 text-xl font-medium text-purple-700">{stage}</h3>

      <div className="mt-8 max-w-md text-center text-gray-600">
        <p>We're creating a custom animated birthday card with your dog. This process may take 1-3 minutes.</p>
        <p className="mt-2">Please don't close this page.</p>
      </div>

      <div className="mt-8 w-full max-w-md">
        <div className="h-2 w-full overflow-hidden rounded-full bg-purple-100">
          <div className="h-full w-full origin-left animate-pulse bg-purple-500"></div>
        </div>
      </div>
    </div>
  )
} 
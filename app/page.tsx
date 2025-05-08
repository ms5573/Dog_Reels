"use client"

import { useState } from "react"
import { Upload, MessageSquare, Gift } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import UploadForm from "@/components/upload-form"
import ProcessingStatus from "@/components/processing-status"
import ResultDisplay from "@/components/result-display"

export default function Home() {
  const [currentStep, setCurrentStep] = useState<"upload" | "processing" | "complete" | "failed">("upload")
  const [taskId, setTaskId] = useState<string | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [processingStage, setProcessingStage] = useState<string>("Uploading...")

  const handleSubmit = async (formData: FormData) => {
    try {
      setCurrentStep("processing")
      setProcessingStage("Uploading...")

      // Submit the form data to the API
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Failed to upload")
      }

      const data = await response.json()
      setTaskId(data.task_id)

      // Start polling for status
      pollStatus(data.task_id)
    } catch (error) {
      console.error("Error submitting form:", error)
      setCurrentStep("failed")
      setErrorMessage("Failed to upload. Please try again.")
    }
  }

  const pollStatus = async (id: string) => {
    try {
      const response = await fetch(`/api/status/${id}`)

      if (!response.ok) {
        throw new Error("Failed to get status")
      }

      const data = await response.json()

      switch (data.status) {
        case "PENDING":
          setProcessingStage("Processing your request...")
          break
        case "PROCESSING":
          setProcessingStage(data.stage || "Creating your birthday card...")
          break
        case "COMPLETE":
          setCurrentStep("complete")
          setResultUrl(data.result_url)
          return // Stop polling
        case "FAILED":
          setCurrentStep("failed")
          setErrorMessage(data.error || "Something went wrong. Please try again.")
          return // Stop polling
        default:
          setProcessingStage("Processing your request...")
      }

      // Continue polling after a delay
      setTimeout(() => pollStatus(id), 5000)
    } catch (error) {
      console.error("Error polling status:", error)
      setCurrentStep("failed")
      setErrorMessage("Failed to check status. Please try again.")
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4 md:p-24 bg-gradient-to-b from-pink-50 to-purple-50">
      <div className="z-10 max-w-5xl w-full items-center justify-between text-sm flex flex-col">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-bold text-purple-600 mb-4">Dog Birthday Card Generator</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Create a personalized, animated digital birthday card featuring your dog dancing to the birthday song!
          </p>
        </div>

        <Card className="w-full max-w-2xl p-6 shadow-xl bg-white">
          {currentStep === "upload" && <UploadForm onSubmit={handleSubmit} />}

          {currentStep === "processing" && <ProcessingStatus stage={processingStage} />}

          {currentStep === "complete" && resultUrl && <ResultDisplay resultUrl={resultUrl} />}

          {currentStep === "failed" && (
            <div className="text-center p-6">
              <div className="text-red-500 text-xl mb-4">
                {errorMessage || "Sorry, something went wrong. Please try again."}
              </div>
              <Button onClick={() => setCurrentStep("upload")} className="bg-purple-600 hover:bg-purple-700">
                Try Again
              </Button>
            </div>
          )}
        </Card>

        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold text-purple-600 mb-4">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="p-4 bg-white rounded-lg shadow-md">
              <div className="bg-purple-100 p-3 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <Upload className="text-purple-600" />
              </div>
              <h3 className="font-semibold text-lg mb-2">Upload Your Dog Photo</h3>
              <p className="text-gray-600">
                Select a clear photo of your dog to transform into a cute dancing animation.
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-md">
              <div className="bg-purple-100 p-3 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <MessageSquare className="text-purple-600" />
              </div>
              <h3 className="font-semibold text-lg mb-2">Add Your Message</h3>
              <p className="text-gray-600">Write a heartfelt birthday message to display alongside the animation.</p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-md">
              <div className="bg-purple-100 p-3 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                <Gift className="text-purple-600" />
              </div>
              <h3 className="font-semibold text-lg mb-2">Get Your Card</h3>
              <p className="text-gray-600">
                Receive a custom HTML birthday card with your dog dancing to the birthday song!
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
} 
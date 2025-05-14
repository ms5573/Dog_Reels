"use client"

import { useState, useEffect } from "react"
import { Upload, MessageSquare, Gift, Sparkles, Cake, Music } from "lucide-react"
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
  const [retryCount, setRetryCount] = useState(0)
  const [pollingActive, setPollingActive] = useState(false)

  // Effect to manage polling when taskId changes
  useEffect(() => {
    if (taskId && currentStep === "processing" && !pollingActive) {
      setPollingActive(true);
      pollStatus(taskId);
    }
    
    return () => {
      setPollingActive(false);
    };
  }, [taskId, currentStep]);

  const handleSubmit = async (formData: FormData) => {
    try {
      setCurrentStep("processing")
      setProcessingStage("Uploading...")
      setRetryCount(0)
      setPollingActive(false)

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
      
      // Polling will be started by the useEffect
    } catch (error) {
      console.error("Error submitting form:", error)
      setCurrentStep("failed")
      setErrorMessage("Failed to upload. Please try again.")
    }
  }

  const pollStatus = async (id: string) => {
    if (!pollingActive) return;
    
    try {
      const response = await fetch(`/api/status/${id}`)

      if (!response.ok) {
        throw new Error("Failed to get status")
      }

      const data = await response.json()
      console.log("Status update:", data)

      switch (data.status) {
        case "PENDING":
          setProcessingStage(data.stage || "Processing your request...")
          scheduleNextPoll(id);
          break;
          
        case "PROCESSING":
          setProcessingStage(data.stage || "Creating your birthday card...")
          // Reset retry count since we got a valid processing status
          setRetryCount(0) 
          scheduleNextPoll(id);
          break;
          
        case "COMPLETE":
          if (data.result_url) {
            setResultUrl(data.result_url)
            setCurrentStep("complete")
            setPollingActive(false)
          } else {
            console.error("Complete status but no result URL")
            scheduleNextPoll(id)
          }
          break;
          
        case "FAILED":
          setCurrentStep("failed")
          setErrorMessage(data.error || "Something went wrong. Please try again.")
          setPollingActive(false)
          break;
          
        default:
          setProcessingStage("Processing your request...")
          scheduleNextPoll(id)
      }
    } catch (error) {
      console.error("Error polling status:", error)
      
      // Increment retry count
      const newRetryCount = retryCount + 1;
      setRetryCount(newRetryCount);
      
      // If we've retried too many times, show error
      if (newRetryCount > 5) {
        setCurrentStep("failed")
        setErrorMessage("Failed to check status. Please try again.")
        setPollingActive(false)
      } else {
        // Otherwise retry after a longer delay
        setTimeout(() => pollStatus(id), 5000 * newRetryCount)
      }
    }
  }
  
  const scheduleNextPoll = (id: string) => {
    if (pollingActive) {
      setTimeout(() => pollStatus(id), 3000)
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4 md:p-24 bg-gradient-to-br from-pink-100 via-purple-50 to-blue-100">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
        <div className="absolute top-0 -right-24 w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob" style={{ animationDelay: '2s' }}></div>
        <div className="absolute -bottom-24 left-1/3 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob" style={{ animationDelay: '4s' }}></div>
      </div>

      <div className="z-10 max-w-5xl w-full items-center justify-between text-sm flex flex-col">
        <div className="text-center mb-12">
          <div className="flex justify-center mb-3">
            <div className="relative">
              <Cake className="h-16 w-16 text-purple-600" />
              <Sparkles className="h-8 w-8 text-yellow-500 absolute -top-2 -right-2 animate-pulse" />
            </div>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold text-purple-600 mb-4">
            Dog Birthday Card Generator
          </h1>
          <p className="text-xl text-gray-700 max-w-2xl mx-auto">
            Transform your beloved pup into an adorable animated character dancing to the birthday song!
          </p>
        </div>

        <Card className="w-full max-w-2xl p-6 shadow-xl bg-white rounded-lg border border-purple-100">
          {currentStep === "upload" && <UploadForm onSubmit={handleSubmit} />}

          {currentStep === "processing" && (
            <>
              <ProcessingStatus stage={processingStage} />
              {retryCount > 0 && (
                <p className="text-amber-600 text-center mt-4">
                  Still working on your birthday card... Thank you for your patience!
                </p>
              )}
            </>
          )}

          {currentStep === "complete" && resultUrl && <ResultDisplay resultUrl={resultUrl} />}

          {currentStep === "failed" && (
            <div className="text-center p-6">
              <div className="text-red-500 text-xl mb-4">
                {errorMessage || "Sorry, something went wrong. Please try again."}
              </div>
              <Button 
                onClick={() => {
                  setCurrentStep("upload");
                  setTaskId(null);
                  setResultUrl(null);
                  setErrorMessage(null);
                }} 
                className="bg-purple-600 hover:bg-purple-700"
              >
                Try Again
              </Button>
            </div>
          )}
        </Card>

        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold text-purple-600 mb-6">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="p-6 bg-white rounded-lg shadow-md border border-purple-100">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Upload className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-lg mb-3 text-purple-700">Upload Your Dog Photo</h3>
              <p className="text-gray-600">
                Select a clear photo of your dog to transform into a cute animated character with AI magic.
              </p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md border border-purple-100">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Music className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-lg mb-3 text-purple-700">Add Birthday Music</h3>
              <p className="text-gray-600">
                Your dog will dance to the classic "Happy Birthday" tune with a party hat and festive animations.
              </p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md border border-purple-100">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Gift className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-lg mb-3 text-purple-700">Share Your Card</h3>
              <p className="text-gray-600">
                Download or share your custom animated birthday card with friends and family for a unique celebration!
              </p>
            </div>
          </div>
        </div>
        
        {/* Hide the preview section when showing a real result */}
        {currentStep !== "complete" && (
          <div className="mt-12 mb-6 p-6 bg-white rounded-lg shadow-md max-w-4xl border border-purple-100">
            <h2 className="text-xl font-bold text-purple-700 mb-3">Preview Example</h2>
            <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
              <div className="text-center p-4">
                <p className="text-gray-500">Preview of your dog's dancing animation will appear here</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
} 
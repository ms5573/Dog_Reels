"use client"

import { useState, useEffect } from "react"
import { Upload, MessageSquare, Gift, Sparkles, Cake, Music, MailCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import UploadForm from "@/components/upload-form"
import ProcessingStatus from "@/components/processing-status"
import ResultDisplay from "@/components/result-display"

export default function Home() {
  const [currentStep, setCurrentStep] = useState<"upload" | "processing" | "complete" | "failed">("upload")
  const [taskId, setTaskId] = useState<string | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [cloudfrontUrl, setCloudfrontUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [processingStage, setProcessingStage] = useState<string>("Uploading...")
  const [retryCount, setRetryCount] = useState(0)
  const [pollingActive, setPollingActive] = useState(false)
  const [videoVerified, setVideoVerified] = useState(false)

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
      setProcessingStage("Uploading your photo and details...")
      setRetryCount(0)
      setPollingActive(false)
      setVideoVerified(false)
      setCloudfrontUrl(null)
      setResultUrl(null)
      setErrorMessage(null)

      // Submit the form data to the API
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Upload request failed" }));
        throw new Error(errorData.error || "Failed to upload")
      }

      const data = await response.json()
      if (data.success && data.task_id) {
        setTaskId(data.task_id)
        // Polling will be started by the useEffect once taskId is set and currentStep is processing
      } else {
        throw new Error(data.message || "Failed to start processing task.")
      }
    } catch (error: any) {
      console.error("Error submitting form:", error)
      setCurrentStep("failed")
      setErrorMessage(error.message || "Failed to upload. Please try again.")
    }
  }

  const pollStatus = async (id: string) => {
    if (currentStep !== 'processing') {
        setPollingActive(false);
        return;
    }
    
    try {
      const response = await fetch(`/api/status/${id}`)

      if (!response.ok) {
        if (response.status === 404 && retryCount < 5) {
             console.warn(`Status 404 for task ${id}, retrying... (attempt ${retryCount + 1})`)
             setProcessingStage("Initializing processing... please wait.")
             const newRetryCount = retryCount + 1;
             setRetryCount(newRetryCount);
             scheduleNextPoll(id, 3000 + (1000 * newRetryCount));
             return;
        }
        throw new Error(`Failed to get status: ${response.statusText}`)
      }

      const data = await response.json()
      console.log("Status update:", data)
      setProcessingStage(data.stage || "Processing your request...")

      switch (data.status) {
        case "PENDING":
          setRetryCount(0) 
          scheduleNextPoll(id);
          break;
          
        case "PROCESSING":
          setRetryCount(0) 
          scheduleNextPoll(id, 2000);
          break;
          
        case "COMPLETE":
          setPollingActive(false);
          if (data.result_url) {
            setResultUrl(data.result_url);
            setCloudfrontUrl(data.result_url);
            setCurrentStep("complete"); 
            setProcessingStage("Video sent to your email!");
          } else {
            console.error("COMPLETE status but no Cloudinary result_url for email.");
            setCurrentStep("failed");
            setErrorMessage("Processing finished, but there was an issue getting the video link for your email. Please contact support.");
          }
          break;
          
        case "FAILED":
          setPollingActive(false);
          setCurrentStep("failed")
          setErrorMessage(data.error || "Video generation failed. Please try again.")
          break;
          
        default:
          console.warn(`Unknown task status received: ${data.status}`);
          setRetryCount(0)
          scheduleNextPoll(id)
      }
    } catch (error: any) {
      console.error("Error polling status:", error)
      const newRetryCount = retryCount + 1;
      setRetryCount(newRetryCount);
      
      if (newRetryCount > 15) {
        setPollingActive(false);
        setCurrentStep("failed")
        setErrorMessage("Failed to get processing status after multiple attempts. Please try again or contact support.")
      } else {
        scheduleNextPoll(id, 3000 + (1000 * newRetryCount));
      }
    }
  }
  
  const scheduleNextPoll = (id: string, delay = 5000) => {
    if (currentStep === 'processing') {
      setTimeout(() => pollStatus(id), delay)
    }
  }

  const resetForm = () => {
    setCurrentStep("upload");
    setTaskId(null);
    setResultUrl(null);
    setCloudfrontUrl(null);
    setErrorMessage(null);
    setVideoVerified(false);
    setProcessingStage("Uploading...");
    setRetryCount(0);
    setPollingActive(false);
  };

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
            You'll receive the final video via email.
          </p>
        </div>

        <Card className="w-full max-w-2xl p-6 shadow-xl bg-white rounded-lg border border-purple-100">
          {currentStep === "upload" && <UploadForm onSubmit={handleSubmit} />}

          {currentStep === "processing" && (
            <ProcessingStatus stage={processingStage} />
          )}
          
          {currentStep === "complete" && (
            <div className="text-center p-6">
                <MailCheck className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-purple-600 mb-3">Video Sent!</h2>
                <p className="text-gray-700 mb-6">
                    Your dog's birthday video has been created and a link to it has been sent to your email address.
                    Please check your inbox (and spam folder, just in case!).
                </p>
                {resultUrl && (
                    <p className="text-sm text-gray-500 mb-6">
                        Direct link (for reference): <a href={resultUrl} target="_blank" rel="noopener noreferrer" className="text-purple-500 hover:underline">{resultUrl}</a>
                    </p>
                )}
                <Button 
                    onClick={resetForm} 
                    className="bg-purple-600 hover:bg-purple-700"
                >
                    Create Another Card
                </Button>
            </div>
          )}

          {currentStep === "failed" && (
            <div className="text-center p-6">
              <div className="text-red-500 text-xl mb-4">
                {errorMessage || "Sorry, something went wrong. Please try again."}
              </div>
              <Button 
                onClick={resetForm} 
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
              <h3 className="font-bold text-lg mb-3 text-purple-700">1. Upload & Email</h3>
              <p className="text-gray-600">
                Select a dog photo, add a birthday message, and provide your email address.
              </p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md border border-purple-100">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Music className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-lg mb-3 text-purple-700">2. AI Magic</h3>
              <p className="text-gray-600">
                Our AI transforms your photo, animates your dog, and adds festive birthday music.
              </p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md border border-purple-100">
              <div className="bg-purple-100 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Gift className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-lg mb-3 text-purple-700">3. Receive & Share</h3>
              <p className="text-gray-600">
                You'll get an email with a link to your unique video, ready to download and share!
              </p>
            </div>
          </div>
        </div>
        
        {(currentStep === "upload" || currentStep === "processing") && (
          <div className="mt-12 mb-6 p-6 bg-white rounded-lg shadow-md max-w-4xl border border-purple-100">
            <h2 className="text-xl font-bold text-purple-700 mb-3">Preview Example</h2>
            <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
              <div className="text-center p-4">
                <p className="text-gray-500">A preview of your dog's dancing animation will appear here after processing.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
} 
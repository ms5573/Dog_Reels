"use client"

// Main page component for Dog Birthday Card Generator
import { useState, useEffect } from "react"
import { Upload, MessageSquare, Gift, Cake, Music, MailCheck } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card } from "../components/ui/card"
import UploadForm from "../components/upload-form"
import ProcessingStatus from "../components/processing-status"
import ResultDisplay from "../components/result-display"

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
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50 to-pink-50">
      {/* Clean background pattern */}
      <div className="absolute inset-0 opacity-30 bg-purple-100"></div>
      
      <div className="relative z-10 container mx-auto px-4 py-8 max-w-6xl">
        {/* Hero Section */}
        <div className="text-center mb-16 animate-gentle-fade">
          {/* Main icon */}
          <div className="flex justify-center mb-8">
            <div className="bg-white p-8 rounded-3xl shadow-2xl border border-purple-100 animate-subtle-glow">
              <Cake className="h-24 w-24 text-purple-600" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-bold gradient-text mb-6 leading-tight">
            🐕 Dog Birthday Card Generator 🎂
          </h1>
          
          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-gray-700 max-w-3xl mx-auto leading-relaxed font-medium mb-8">
            Transform your beloved pup into an adorable{" "}
            <span className="text-purple-600 font-bold">animated character</span>{" "}
            dancing to the birthday song! ✨
            <br />
            <span className="text-lg text-gray-600 mt-2 block">You'll receive the magical video via email 📧</span>
          </p>
          
          {/* Feature badges */}
          <div className="flex flex-wrap justify-center gap-4">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl px-6 py-3 shadow-lg border border-purple-100">
              <span className="text-purple-600 font-semibold">🎵 AI-Powered</span>
            </div>
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl px-6 py-3 shadow-lg border border-pink-100">
              <span className="text-pink-600 font-semibold">⚡ 2-3 Minutes</span>
            </div>
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl px-6 py-3 shadow-lg border border-blue-100">
              <span className="text-blue-600 font-semibold">💌 Email Delivery</span>
            </div>
          </div>
        </div>

        {/* Main Card */}
        <Card className="w-full max-w-4xl mx-auto mb-16 shadow-2xl border-0 overflow-hidden">
          <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-1 rounded-2xl">
            <div className="bg-white rounded-2xl">
              <div className="p-8 md:p-12">
                {currentStep === "upload" && <UploadForm onSubmit={handleSubmit} />}

                {currentStep === "processing" && (
                  <div className="text-center">
                    <ProcessingStatus stage={processingStage} />
                    <div className="mt-8">
                      <div className="spinner mx-auto mb-4"></div>
                      <p className="text-gray-600 text-lg">
                        🎨 Creating magic for your furry friend...
                      </p>
                    </div>
                  </div>
                )}
                
                {currentStep === "complete" && (
                  <div className="text-center p-8">
                    <div className="mb-8">
                      <div className="bg-green-100 p-6 rounded-full w-32 h-32 flex items-center justify-center mx-auto mb-6">
                        <MailCheck className="h-16 w-16 text-green-600" />
                      </div>
                    </div>
                    <h2 className="text-4xl font-bold gradient-text mb-6">🎉 Video Sent! 🎉</h2>
                    <p className="text-xl text-gray-700 mb-8 leading-relaxed">
                      Your dog's birthday video has been created and a link has been sent to your email! 
                      <br />
                      <span className="text-purple-600 font-semibold mt-2 block">Check your inbox (and spam folder, just in case!) 📬</span>
                    </p>
                    {resultUrl && (
                      <div className="bg-purple-50 p-6 rounded-xl mb-8 border border-purple-200">
                        <p className="text-sm text-gray-600 mb-3 font-medium">Direct link for reference:</p>
                        <a href={resultUrl} target="_blank" rel="noopener noreferrer" 
                           className="text-purple-600 hover:text-purple-800 underline break-all text-sm">
                          {resultUrl}
                        </a>
                      </div>
                    )}
                    <Button 
                      onClick={resetForm} 
                      className="btn-primary text-white font-bold py-4 px-8 text-lg rounded-2xl"
                    >
                      🐾 Create Another Card 🐾
                    </Button>
                  </div>
                )}

                {currentStep === "failed" && (
                  <div className="text-center p-8">
                    <div className="text-red-600 text-xl mb-8 bg-red-50 p-6 rounded-xl border border-red-200">
                      😔 {errorMessage || "Sorry, something went wrong. Please try again."}
                    </div>
                    <Button 
                      onClick={resetForm} 
                      className="btn-primary text-white font-bold py-4 px-8 text-lg rounded-2xl"
                    >
                      🔄 Try Again 🔄
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* How It Works Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold gradient-text mb-4">
            ✨ How It Works ✨
          </h2>
          <p className="text-xl text-gray-600 mb-12">Simple, fast, and absolutely adorable!</p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="card-hover bg-white rounded-3xl p-8 shadow-xl border border-purple-100">
              <div className="bg-gradient-to-br from-purple-100 to-purple-200 p-6 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-6">
                <Upload className="h-10 w-10 text-purple-600" />
              </div>
              <h3 className="font-bold text-2xl mb-4 text-purple-700">1. Upload & Email 📸</h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Select a dog photo, add a birthday message, and provide your email address.
              </p>
            </div>
            
            <div className="card-hover bg-white rounded-3xl p-8 shadow-xl border border-pink-100">
              <div className="bg-gradient-to-br from-pink-100 to-pink-200 p-6 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-6">
                <Music className="h-10 w-10 text-pink-600" />
              </div>
              <h3 className="font-bold text-2xl mb-4 text-pink-700">2. AI Magic 🤖</h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                Our AI transforms your photo, animates your dog, and adds festive birthday music.
              </p>
            </div>
            
            <div className="card-hover bg-white rounded-3xl p-8 shadow-xl border border-green-100">
              <div className="bg-gradient-to-br from-green-100 to-green-200 p-6 rounded-2xl w-20 h-20 flex items-center justify-center mx-auto mb-6">
                <Gift className="h-10 w-10 text-green-600" />
              </div>
              <h3 className="font-bold text-2xl mb-4 text-green-700">3. Receive & Share 🎁</h3>
              <p className="text-gray-600 text-lg leading-relaxed">
                You'll get an email with a link to your unique video, ready to download and share!
              </p>
            </div>
          </div>
        </div>
        
        {/* Preview Section */}
        {(currentStep === "upload" || currentStep === "processing") && (
          <div className="mb-16">
            <div className="bg-white rounded-3xl shadow-xl p-8 border border-purple-100">
              <h2 className="text-3xl font-bold gradient-text mb-6 text-center">🎬 Preview Example</h2>
              <div className="aspect-video bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl flex items-center justify-center">
                <div className="text-center p-8">
                  <Cake className="h-16 w-16 text-purple-500 mx-auto mb-4" />
                  <p className="text-purple-600 text-xl font-semibold mb-2">
                    🎵 A preview of your dog's dancing animation will appear here after processing! 🕺
                  </p>
                  <p className="text-gray-500">Get ready for some serious cuteness! 🥰</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center">
          <p className="text-gray-500 text-lg">
            Made with 💖 for dog lovers everywhere • Powered by AI ✨
          </p>
        </div>
      </div>
    </main>
  )
}
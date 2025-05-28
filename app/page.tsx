"use client"

// Main page component for Pet Reel Generator
import { useState, useEffect } from "react"
import { Upload, MessageSquare, Gift, Video, Music, MailCheck, CreditCard } from "lucide-react"
import { Button } from "../components/ui/button"
import { Card } from "../components/ui/card"
import { Elements } from '@stripe/react-stripe-js'
import { stripePromise, PAYMENT_AMOUNT_DOLLARS } from '@/lib/stripe-client'
import UploadForm from "../components/upload-form"
import PaymentForm from "../components/payment-form"
import ProcessingStatus from "../components/processing-status"
import ResultDisplay from "../components/result-display"

export default function Home() {
  const [currentStep, setCurrentStep] = useState<"upload" | "payment" | "processing" | "complete" | "failed">("upload")
  const [taskId, setTaskId] = useState<string | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [cloudfrontUrl, setCloudfrontUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [processingStage, setProcessingStage] = useState<string>("Uploading...")
  const [retryCount, setRetryCount] = useState(0)
  const [pollingActive, setPollingActive] = useState(false)
  const [videoVerified, setVideoVerified] = useState(false)

  // Form data storage
  const [formData, setFormData] = useState<FormData | null>(null)
  const [userEmail, setUserEmail] = useState<string>("")
  const [petName, setPetName] = useState<string>("")
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null)

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

  const handleUploadSubmit = async (uploadFormData: FormData) => {
    try {
      // Extract form data for payment step
      const email = uploadFormData.get('email') as string
      const message = uploadFormData.get('message') as string
      const petNameFromMessage = message ? message.split(' ')[0] : 'your pet' // Simple extraction

      setFormData(uploadFormData)
      setUserEmail(email)
      setPetName(petNameFromMessage)
      setCurrentStep("payment")
    } catch (error: any) {
      console.error("Error preparing form data:", error)
      setCurrentStep("failed")
      setErrorMessage(error.message || "Failed to prepare form data. Please try again.")
    }
  }

  const handlePaymentSuccess = async (paymentId: string) => {
    setPaymentIntentId(paymentId)
    
    try {
      if (!formData) {
        throw new Error("Form data not found")
      }

      setCurrentStep("processing")
      setProcessingStage("Payment confirmed! Starting video generation...")
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
      setErrorMessage(error.message || "Failed to start video generation. Please try again.")
    }
  }

  const handlePaymentError = (error: string) => {
    setCurrentStep("failed")
    setErrorMessage(`Payment failed: ${error}`)
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
    setFormData(null);
    setUserEmail("");
    setPetName("");
    setPaymentIntentId(null);
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
              <Video className="h-24 w-24 text-purple-600" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-bold gradient-text mb-6 leading-tight">
            🐾 Pet Reel Generator 🎂
          </h1>
          
          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-gray-700 max-w-3xl mx-auto leading-relaxed font-medium mb-8">
            Transform your beloved pet into an adorable{" "}
            <span className="text-purple-600 font-bold">animated character</span>{" "}
            in magical Studio Ghibli style! ✨
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
                {currentStep === "upload" && <UploadForm onSubmit={handleUploadSubmit} />}

                {currentStep === "payment" && (
                  <div className="text-center">
                    <div className="mb-8">
                      <div className="bg-gradient-to-br from-green-100 to-green-200 p-6 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
                        <CreditCard className="h-10 w-10 text-green-600" />
                      </div>
                      <h2 className="text-3xl font-bold gradient-text mb-4">💳 Secure Payment</h2>
                      <p className="text-gray-600 text-lg mb-2">
                        Almost there! Just ${PAYMENT_AMOUNT_DOLLARS} to create your pet's magical reel
                      </p>
                      <p className="text-sm text-gray-500">
                        Video will be generated after payment confirmation
                      </p>
                    </div>
                    
                    <Elements stripe={stripePromise}>
                      <PaymentForm 
                        email={userEmail}
                        petName={petName}
                        onPaymentSuccess={handlePaymentSuccess}
                        onPaymentError={handlePaymentError}
                      />
                    </Elements>
                    
                    <div className="mt-6">
                      <Button 
                        onClick={() => setCurrentStep("upload")} 
                        variant="outline"
                        className="text-gray-600 hover:text-gray-800"
                      >
                        ← Back to Upload
                      </Button>
                    </div>
                  </div>
                )}

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
                      Your pet's magical reel has been created and a link has been sent to your email! 
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
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="card-hover bg-white rounded-3xl p-6 shadow-xl border border-purple-100">
              <div className="bg-gradient-to-br from-purple-100 to-purple-200 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Upload className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="font-bold text-xl mb-3 text-purple-700">1. Upload 📸</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Select a pet photo, describe what they should be doing, and provide your email address.
              </p>
            </div>
            
            <div className="card-hover bg-white rounded-3xl p-6 shadow-xl border border-green-100">
              <div className="bg-gradient-to-br from-green-100 to-green-200 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <CreditCard className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="font-bold text-xl mb-3 text-green-700">2. Pay 💳</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Secure payment through Stripe. Your video is generated instantly after confirmation.
              </p>
            </div>
            
            <div className="card-hover bg-white rounded-3xl p-6 shadow-xl border border-pink-100">
              <div className="bg-gradient-to-br from-pink-100 to-pink-200 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="h-8 w-8 text-pink-600" />
              </div>
              <h3 className="font-bold text-xl mb-3 text-pink-700">3. AI Magic 🤖</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Our AI transforms your photo into Studio Ghibli style and animates your pet doing the action you described.
              </p>
            </div>
            
            <div className="card-hover bg-white rounded-3xl p-6 shadow-xl border border-blue-100">
              <div className="bg-gradient-to-br from-blue-100 to-blue-200 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Gift className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="font-bold text-xl mb-3 text-blue-700">4. Receive & Share ��</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                You'll get an email with a link to your unique video, ready to download and share!
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-gray-500 text-lg">
            Made with 💖 for pet lovers everywhere • Powered by AI ✨
          </p>
        </div>
      </div>
    </main>
  )
}
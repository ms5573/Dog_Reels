"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Upload, X, Camera, ArrowRight, MessageSquare, Mail } from "lucide-react"
import { Button } from "./ui/button"
import { Textarea } from "./ui/textarea"
import { Label } from "./ui/label"
import { Input } from "./ui/input"

interface UploadFormProps {
  onSubmit: (formData: FormData) => void
}

export default function UploadForm({ onSubmit }: UploadFormProps) {
  const [message, setMessage] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState("")
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setError(null)

    if (!file) {
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    // Check if file is an image
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (JPG, PNG, etc.)")
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError("File size should be less than 5MB")
      setSelectedFile(null)
      setPreviewUrl(null)
      return
    }

    setSelectedFile(file)

    // Create preview URL
    const reader = new FileReader()
    reader.onloadend = () => {
      setPreviewUrl(reader.result as string)
    }
    reader.readAsDataURL(file)
  }

  const clearFile = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const isValidEmail = (email: string) => {
    // Basic email validation regex
    return /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/.test(email);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!selectedFile) {
      setError("Please select a dog photo")
      return
    }

    if (!message.trim()) {
      setError("Please enter a birthday message")
      return
    }

    if (!userEmail.trim()) {
      setError("Please enter your email address")
      return
    }

    if (!isValidEmail(userEmail)) {
        setError("Please enter a valid email address")
        return
    }

    const formData = new FormData()
    formData.append("dogPhoto", selectedFile)
    formData.append("message", message)
    formData.append("email", userEmail)

    onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold gradient-text mb-3">
          🎨 Create Your Dog's Birthday Card 🎂
        </h2>
        <p className="text-lg text-gray-600">Fill out the form below to get started!</p>
      </div>
      
      {/* Photo upload section */}
      <div className="space-y-4">
        <Label htmlFor="dogPhoto" className="text-xl font-bold text-purple-800 flex items-center gap-2">
          <Camera className="h-6 w-6" /> 📷 Upload a Photo of Your Dog
        </Label>

        {!previewUrl ? (
          <div
            className="border-2 border-dashed border-purple-300 bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-12 text-center cursor-pointer hover:border-purple-400 hover:bg-gradient-to-br hover:from-purple-100 hover:to-pink-100 transition-all duration-200"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="bg-gradient-to-br from-purple-500 to-pink-500 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
              <Upload className="h-10 w-10 text-white" />
            </div>
            <p className="text-purple-700 font-bold text-lg mb-2">📤 Click to upload or drag and drop</p>
            <p className="text-purple-600 text-base">JPG, PNG (Max 5MB) • Let's see that adorable face! 🐕</p>
            
            <input
              id="dogPhoto"
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        ) : (
          <div className="relative rounded-2xl overflow-hidden border-4 border-purple-300 shadow-xl bg-white">
            <img
              src={previewUrl || "/placeholder.svg"}
              alt="Dog preview"
              className="w-full h-64 object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-purple-900/70 via-transparent to-transparent flex items-end">
              <div className="p-6 text-white w-full">
                <p className="font-bold text-lg mb-1">Your dog looks absolutely amazing! 🌟</p>
                <p className="text-purple-200">Ready to become an animated dancing star! 💃</p>
              </div>
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="absolute top-4 right-4 bg-red-500 text-white p-2 rounded-full hover:bg-red-600 shadow-lg transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}
      </div>

      {/* Message section */}
      <div className="space-y-4">
        <Label htmlFor="message" className="text-xl font-bold text-purple-800 flex items-center gap-2">
          <MessageSquare className="h-6 w-6" /> 💬 Birthday Message
        </Label>
        <Textarea
          id="message"
          placeholder="🎉 Write a heartfelt birthday wish here... Make it special! ✨"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="min-h-[120px] resize-y border-2 border-purple-300 focus:border-purple-500 hover:border-purple-400 rounded-xl p-4 text-lg bg-gradient-to-br from-white to-purple-50 focus:from-white focus:to-pink-50 transition-all"
        />
        <p className="text-sm text-purple-600 bg-purple-50 p-3 rounded-lg border border-purple-200">
          💡 Tip: The more personal, the better! Mention their favorite treats or toys!
        </p>
      </div>

      {/* Email section */}
      <div className="space-y-4">
        <Label htmlFor="userEmail" className="text-xl font-bold text-purple-800 flex items-center gap-2">
          <Mail className="h-6 w-6" /> 📧 Your Email Address
        </Label>
        <Input
          id="userEmail"
          type="email"
          placeholder="your.email@example.com"
          value={userEmail}
          onChange={(e) => setUserEmail(e.target.value)}
          className="border-2 border-purple-300 focus:border-purple-500 hover:border-purple-400 rounded-xl p-4 text-lg bg-gradient-to-r from-white to-purple-50 focus:from-white focus:to-pink-50 transition-all"
        />
        <p className="text-sm text-purple-600 bg-purple-50 p-3 rounded-lg border border-purple-200">
          📬 We'll send the final magical video link to this email address!
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="text-red-600 text-base p-4 bg-gradient-to-r from-red-50 to-pink-50 border-2 border-red-200 rounded-xl">
          <div className="flex items-center gap-2">
            <span className="text-2xl">😅</span>
            <span className="font-semibold">{error}</span>
          </div>
        </div>
      )}

      {/* Submit button */}
      <div className="pt-4">
        <Button
          type="submit"
          className="w-full btn-primary text-white text-xl font-bold py-6 rounded-2xl shadow-xl"
          disabled={!selectedFile || !message.trim() || !userEmail.trim() || !isValidEmail(userEmail)}
        >
          <div className="flex items-center justify-center gap-3">
            <span>🎬 Create My Dog's Birthday Video! 🎂</span>
            <ArrowRight className="h-6 w-6" />
          </div>
        </Button>
        
        {(selectedFile && message.trim() && userEmail.trim() && isValidEmail(userEmail)) && (
          <p className="text-center text-purple-600 mt-4 font-semibold">
            🚀 Ready to launch! Click the button above to start the magic! ✨
          </p>
        )}
      </div>
    </form>
  )
} 
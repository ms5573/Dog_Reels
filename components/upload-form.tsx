"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Upload, X, Camera, Image, ArrowRight, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

interface UploadFormProps {
  onSubmit: (formData: FormData) => void
}

export default function UploadForm({ onSubmit }: UploadFormProps) {
  const [message, setMessage] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
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

    const formData = new FormData()
    formData.append("dogPhoto", selectedFile)
    formData.append("message", message)

    onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold text-purple-600 mb-1">
          Create Your Dog's Birthday Card
        </h2>
        <p className="text-gray-600">Fill out the form below to get started!</p>
      </div>
      
      <div className="space-y-3">
        <Label htmlFor="dogPhoto" className="text-lg font-medium text-purple-800 flex items-center gap-2">
          <Camera className="h-5 w-5" /> Upload a Photo of Your Dog
        </Label>

        {!previewUrl ? (
          <div
            className="border-2 border-dashed border-purple-400 bg-purple-50 rounded-lg p-8 text-center cursor-pointer hover:bg-purple-100 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="bg-white w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-3 shadow-md">
              <Upload className="h-8 w-8 text-purple-500" />
            </div>
            <p className="text-purple-700 font-medium mb-1">Click to upload or drag and drop</p>
            <p className="text-sm text-purple-600">JPG, PNG (Max 5MB)</p>
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
          <div className="relative rounded-lg overflow-hidden border-2 border-purple-300 shadow-md">
            <img
              src={previewUrl || "/placeholder.svg"}
              alt="Dog preview"
              className="w-full h-56 object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-purple-900/60 to-transparent flex items-end">
              <div className="p-3 text-white">
                <p className="font-medium">Your dog looks great!</p>
                <p className="text-sm text-purple-100">Ready to become an animated star</p>
              </div>
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="absolute top-2 right-2 bg-red-500 text-white p-1.5 rounded-full hover:bg-red-600 shadow-md"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <Label htmlFor="message" className="text-lg font-medium text-purple-800 flex items-center gap-2">
          <MessageSquare className="h-5 w-5" /> Birthday Message
        </Label>
        <Textarea
          id="message"
          placeholder="Write a heartfelt birthday wish here..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="min-h-[100px] resize-y border-2 border-purple-300 focus:border-purple-500 rounded-lg p-3"
        />
      </div>

      {error && (
        <div className="text-red-500 text-sm p-3 bg-red-50 border border-red-200 rounded-lg">
          {error}
        </div>
      )}

      <Button
        type="submit"
        className="w-full bg-purple-600 hover:bg-purple-700 text-lg py-3 rounded-lg shadow-md"
        disabled={!selectedFile || !message.trim()}
      >
        Create My Dog's Birthday Card! <ArrowRight className="ml-2 h-5 w-5" />
      </Button>
    </form>
  )
} 
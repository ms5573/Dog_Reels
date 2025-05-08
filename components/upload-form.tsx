"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Upload, X } from "lucide-react"
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
      <div className="space-y-2">
        <Label htmlFor="dogPhoto" className="text-lg font-medium">
          Upload a Photo of Your Dog
        </Label>

        {!previewUrl ? (
          <div
            className="border-2 border-dashed border-purple-300 rounded-lg p-8 text-center cursor-pointer hover:bg-purple-50 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mx-auto h-12 w-12 text-purple-400 mb-2" />
            <p className="text-sm text-gray-600 mb-1">Click to upload or drag and drop</p>
            <p className="text-xs text-gray-500">JPG, PNG (Max 5MB)</p>
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
          <div className="relative">
            <img
              src={previewUrl || "/placeholder.svg"}
              alt="Dog preview"
              className="w-full h-48 object-contain rounded-lg border border-purple-200"
            />
            <button
              type="button"
              onClick={clearFile}
              className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="message" className="text-lg font-medium">
          Birthday Message
        </Label>
        <Textarea
          id="message"
          placeholder="Enter your birthday message here..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="min-h-[100px] resize-y"
        />
      </div>

      {error && <div className="text-red-500 text-sm">{error}</div>}

      <Button
        type="submit"
        className="w-full bg-purple-600 hover:bg-purple-700"
        disabled={!selectedFile || !message.trim()}
      >
        Create My Birthday Card!
      </Button>
    </form>
  )
} 
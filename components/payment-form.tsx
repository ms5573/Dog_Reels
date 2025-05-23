"use client"

import React, { useState } from 'react'
import { useStripe, useElements, CardElement } from '@stripe/react-stripe-js'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CreditCard, Shield, Lock } from 'lucide-react'
import { PAYMENT_AMOUNT_DOLLARS } from '@/lib/stripe-client'

interface PaymentFormProps {
  email: string
  dogName?: string
  onPaymentSuccess: (paymentIntentId: string) => void
  onPaymentError: (error: string) => void
}

export default function PaymentForm({ email, dogName, onPaymentSuccess, onPaymentError }: PaymentFormProps) {
  const stripe = useStripe()
  const elements = useElements()
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!stripe || !elements) {
      setError('Stripe has not loaded yet. Please try again.')
      return
    }

    const cardElement = elements.getElement(CardElement)
    if (!cardElement) {
      setError('Card element not found.')
      return
    }

    setIsProcessing(true)

    try {
      // Create payment intent
      const response = await fetch('/api/create-payment-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, dogName })
      })

      const { success, clientSecret, error: apiError } = await response.json()

      if (!success || !clientSecret) {
        throw new Error(apiError || 'Failed to create payment intent')
      }

      // Confirm payment immediately after creation
      console.log('Confirming payment with client secret:', clientSecret.substring(0, 10) + '...')
      const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: cardElement,
          billing_details: {
            email: email,
          },
        },
        return_url: window.location.origin, // Add return URL for 3D Secure
      })

      console.log('Payment confirmation result:', {
        error: stripeError ? {
          message: stripeError.message,
          type: stripeError.type,
          code: stripeError.code
        } : null,
        paymentIntent: paymentIntent ? {
          id: paymentIntent.id,
          status: paymentIntent.status,
          amount: paymentIntent.amount
        } : null
      })

      if (stripeError) {
        if (stripeError.type === 'card_error') {
          throw new Error(stripeError.message || 'Your card was declined')
        } else {
          throw new Error(stripeError.message || 'Payment failed')
        }
      }

      if (paymentIntent?.status === 'succeeded') {
        onPaymentSuccess(paymentIntent.id)
      } else if (paymentIntent?.status === 'requires_action') {
        // Handle 3D Secure authentication
        const { error: actionError } = await stripe.handleCardAction(clientSecret)
        if (actionError) {
          throw new Error(actionError.message || '3D Secure authentication failed')
        }
        onPaymentSuccess(paymentIntent.id)
      } else {
        throw new Error('Payment was not completed successfully')
      }
    } catch (err: any) {
      const errorMessage = err.message || 'An unexpected error occurred'
      console.error('Payment error:', errorMessage)
      setError(errorMessage)
      onPaymentError(errorMessage)
    } finally {
      setIsProcessing(false)
    }
  }

  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': {
          color: '#aab7c4',
        },
        backgroundColor: '#white',
      },
      invalid: {
        color: '#9e2146',
      },
    },
    hidePostalCode: false,
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <Card className="p-6 border-2 border-purple-200 shadow-xl">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="bg-gradient-to-br from-green-100 to-green-200 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <CreditCard className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-2xl font-bold text-purple-700 mb-2">Secure Payment</h3>
          <p className="text-gray-600">
            Complete your payment to create your dog's magical birthday video
          </p>
        </div>

        {/* Order Summary */}
        <div className="bg-purple-50 rounded-xl p-4 mb-6 border border-purple-200">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-700 font-medium">Dog Birthday Video</span>
            <span className="text-2xl font-bold text-purple-600">${PAYMENT_AMOUNT_DOLLARS}</span>
          </div>
          {dogName && (
            <p className="text-sm text-gray-600">For: {dogName} 🐕</p>
          )}
          <p className="text-sm text-gray-600">Email: {email}</p>
        </div>

        {/* Payment Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="bg-white rounded-lg border-2 border-gray-200 p-4 focus-within:border-purple-400 transition-colors">
            <CardElement options={cardElementOptions} />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            disabled={!stripe || isProcessing}
            className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-bold py-3 text-lg rounded-xl shadow-lg"
          >
            {isProcessing ? (
              <div className="flex items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Processing...
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2">
                <Lock className="h-5 w-5" />
                Pay ${PAYMENT_AMOUNT_DOLLARS} Securely
              </div>
            )}
          </Button>
        </form>

        {/* Security Notice */}
        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
          <Shield className="h-4 w-4" />
          <span>Powered by Stripe • Your payment is secure and encrypted</span>
        </div>
      </Card>
    </div>
  )
} 
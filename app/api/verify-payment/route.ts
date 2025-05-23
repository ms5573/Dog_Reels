import { NextRequest, NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { paymentIntentId } = body

    if (!paymentIntentId) {
      return NextResponse.json(
        { success: false, error: 'Payment intent ID is required' },
        { status: 400 }
      )
    }

    // Retrieve the payment intent from Stripe
    const paymentIntent = await stripe.paymentIntents.retrieve(paymentIntentId)

    // Check if payment was successful
    if (paymentIntent.status === 'succeeded') {
      return NextResponse.json({
        success: true,
        paymentStatus: 'succeeded',
        amount: paymentIntent.amount,
        email: paymentIntent.metadata.email,
        dogName: paymentIntent.metadata.dogName
      })
    } else {
      return NextResponse.json({
        success: false,
        paymentStatus: paymentIntent.status,
        error: 'Payment not completed'
      })
    }
  } catch (error: any) {
    console.error('Error verifying payment:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to verify payment',
        details: error.message 
      },
      { status: 500 }
    )
  }
} 
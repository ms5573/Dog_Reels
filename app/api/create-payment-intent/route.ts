import { NextRequest, NextResponse } from 'next/server'
import { stripe, PAYMENT_AMOUNT } from '@/lib/stripe'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, dogName } = body

    // Create a payment intent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: PAYMENT_AMOUNT, // Amount in cents
      currency: 'usd',
      description: `Dog Birthday Video for ${dogName || 'your pup'}`,
      metadata: {
        email: email || 'unknown',
        dogName: dogName || 'unknown',
        product: 'dog-birthday-video'
      },
      automatic_payment_methods: {
        enabled: true,
      },
    })

    return NextResponse.json({
      success: true,
      clientSecret: paymentIntent.client_secret,
      amount: PAYMENT_AMOUNT,
      currency: 'usd'
    })
  } catch (error: any) {
    console.error('Error creating payment intent:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to create payment intent',
        details: error.message 
      },
      { status: 500 }
    )
  }
} 
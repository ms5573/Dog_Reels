import { NextRequest, NextResponse } from 'next/server'
import { stripe, PAYMENT_AMOUNT } from '@/lib/stripe'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, petName } = body

    console.log('Creating payment intent with:', {
      amount: PAYMENT_AMOUNT,
      email,
      petName,
      stripeKeyPrefix: process.env.STRIPE_SECRET_KEY?.substring(0, 7) // Log just the prefix for security
    })

    // Create a payment intent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: PAYMENT_AMOUNT, // Amount in cents
      currency: 'usd',
      description: `Pet Reel Video for ${petName || 'your pet'}`,
      metadata: {
        email: email || 'unknown',
        petName: petName || 'unknown',
        product: 'pet-reel-video'
      },
      automatic_payment_methods: {
        enabled: true,
        allow_redirects: 'always'
      },
      confirm: false, // Don't confirm immediately
      capture_method: 'automatic',
      setup_future_usage: 'off_session'
    })

    console.log('Payment intent created:', {
      id: paymentIntent.id,
      status: paymentIntent.status,
      amount: paymentIntent.amount,
      client_secret: paymentIntent.client_secret?.substring(0, 10) + '...'
    })

    return NextResponse.json({
      success: true,
      clientSecret: paymentIntent.client_secret,
      amount: PAYMENT_AMOUNT,
      currency: 'usd'
    })
  } catch (error: any) {
    console.error('Error creating payment intent:', {
      message: error.message,
      type: error.type,
      code: error.code,
      stripeKeyPrefix: process.env.STRIPE_SECRET_KEY?.substring(0, 7)
    })
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
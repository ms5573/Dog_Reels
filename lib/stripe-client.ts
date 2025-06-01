import { loadStripe } from '@stripe/stripe-js'

if (!process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY) {
  throw new Error('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set in environment variables')
}

// Initialize Stripe.js with publishable key
export const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)

// Payment amount for display (in dollars)
export const PAYMENT_AMOUNT_DOLLARS = (parseInt(process.env.PAYMENT_AMOUNT || '199') / 100).toFixed(2) 
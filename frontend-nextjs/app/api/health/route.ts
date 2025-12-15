// Health check API endpoint for Docker
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // Check if we can reach the backend
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    
    let backendStatus = 'unknown'
    try {
      const response = await fetch(`${backendUrl}/health`, { 
        cache: 'no-store',
        signal: AbortSignal.timeout(5000) 
      })
      backendStatus = response.ok ? 'healthy' : 'unhealthy'
    } catch {
      backendStatus = 'unreachable'
    }

    return NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      backend: backendStatus,
      environment: process.env.NODE_ENV || 'development'
    })
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    )
  }
}

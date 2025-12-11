"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function TestAPI() {
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const testAPI = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const url = "http://localhost:8000/api/v1/market-data/?symbol=BTCUSDT&interval=1h&limit=5"
      console.log("Fetching:", url)
      
      const response = await fetch(url)
      console.log("Response status:", response.status)
      console.log("Response headers:", response.headers)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      console.log("Data received:", data)
      setResult(data)
    } catch (err) {
      console.error("Error:", err)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-8">
      <Card>
        <CardHeader>
          <CardTitle>API Test Page</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={testAPI} disabled={loading}>
            {loading ? "Testing..." : "Test API"}
          </Button>

          {error && (
            <div className="bg-red-500/10 border border-red-500 p-4 rounded">
              <p className="font-bold text-red-500">Error:</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {result && (
            <div className="bg-green-500/10 border border-green-500 p-4 rounded">
              <p className="font-bold text-green-500">Success!</p>
              <pre className="text-xs mt-2 overflow-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

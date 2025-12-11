"use client"

import type { Metadata } from "next"
import { useState, useEffect } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import BitcoinIcon from "@/components/icons/bitcoin"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  ReferenceLine,
} from "recharts"
import { format } from "date-fns"

interface TechnicalData {
  date: string
  timestamp: string
  close: number
  rsi: number | null
  macd: number | null
  macd_signal: number | null
  macd_histogram: number | null
  bb_upper: number | null
  bb_middle: number | null
  bb_lower: number | null
}

export default function TechnicalAnalysis() {
  const [dateRange, setDateRange] = useState("7D") // Start with 7D for faster initial load
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<TechnicalData[]>([])

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const daysMap: Record<string, number> = { "7D": 7, "30D": 30, "90D": 90 }
        const days = daysMap[dateRange] || 7
        
        const end = new Date()
        const start = new Date()
        start.setDate(start.getDate() - days)

        const url = `http://localhost:8000/api/v1/analysis/indicators?symbol=BTCUSDT&interval=1h&start=${start.toISOString()}&end=${end.toISOString()}`
        
        const response = await fetch(url)
        if (!response.ok) throw new Error("Failed to fetch indicators")

        const json = await response.json()
        const indicators = json.indicators || []

        const transformed = indicators.map((item: any) => ({
          date: format(new Date(item.timestamp), "MMM d HH:mm"),
          timestamp: item.timestamp,
          close: item.close,
          rsi: item.rsi,
          macd: item.macd,
          macd_signal: item.macd_signal,
          macd_histogram: item.macd_histogram,
          bb_upper: item.bb_upper,
          bb_middle: item.bb_middle,
          bb_lower: item.bb_lower,
        }))

        // Filter out initial null values for cleaner charts
        // RSI needs 14 periods, MACD needs 26, BB needs 20
        const filteredData = transformed.filter((item: any) => 
          item.rsi !== null && item.macd !== null && item.bb_middle !== null
        )

        setData(filteredData)
      } catch (err) {
        console.error("Error fetching indicators:", err)
        setError(err instanceof Error ? err.message : "Failed to load data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [dateRange])

  if (isLoading) {
    return (
      <DashboardPageLayout
        header={{
          title: "Technical Analysis",
          description: "Loading indicators...",
          icon: BitcoinIcon,
        }}
      >
        <Skeleton className="h-96 mb-4" />
        <Skeleton className="h-96 mb-4" />
        <Skeleton className="h-96" />
      </DashboardPageLayout>
    )
  }

  if (error) {
    return (
      <DashboardPageLayout
        header={{
          title: "Technical Analysis",
          description: "Error loading data",
          icon: BitcoinIcon,
        }}
      >
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Failed to Load Data</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{error}</p>
            <Button onClick={() => window.location.reload()} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </DashboardPageLayout>
    )
  }

  const latest = data[data.length - 1]
  const rsiValue = latest?.rsi || 0
  const rsiSignal = rsiValue > 70 ? "Overbought" : rsiValue < 30 ? "Oversold" : "Neutral"
  const rsiColor = rsiValue > 70 ? "text-red-500" : rsiValue < 30 ? "text-green-500" : "text-yellow-500"

  return (
    <DashboardPageLayout
      header={{
        title: "Technical Analysis",
        description: "RSI, MACD, Bollinger Bands and trend indicators",
        icon: BitcoinIcon,
      }}
    >
      {/* Filters */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Time Range</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="inline-flex gap-1 p-1 bg-muted rounded-md">
            {["7D", "30D", "90D"].map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  dateRange === range
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-background"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* RSI Chart */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">RSI (Relative Strength Index)</CardTitle>
          <CardDescription className="text-xs">
            Current: <span className={`font-bold ${rsiColor}`}>{rsiValue.toFixed(1)}</span> - {rsiSignal}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  interval={Math.floor(data.length / 8)}
                />
                <YAxis stroke="#9ca3af" tick={{ fill: "#9ca3af", fontSize: 11 }} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                  }}
                />
                <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" label="Overbought" />
                <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" label="Oversold" />
                <ReferenceLine y={50} stroke="#6b7280" strokeDasharray="3 3" />
                <Line type="monotone" dataKey="rsi" stroke="#f7931a" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* MACD Chart */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">MACD (Moving Average Convergence Divergence)</CardTitle>
          <CardDescription className="text-xs">Trend momentum indicator</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  interval={Math.floor(data.length / 8)}
                />
                <YAxis stroke="#9ca3af" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                  }}
                />
                <Bar dataKey="macd_histogram" fill="#6b7280" opacity={0.6} isAnimationActive={false} />
                <Line type="monotone" dataKey="macd" stroke="#f7931a" strokeWidth={2} dot={false} name="MACD" isAnimationActive={false} />
                <Line type="monotone" dataKey="macd_signal" stroke="#3b82f6" strokeWidth={2} dot={false} name="Signal" isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Bollinger Bands */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Bollinger Bands</CardTitle>
          <CardDescription className="text-xs">Volatility and price range indicator</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  interval={Math.floor(data.length / 8)}
                />
                <YAxis 
                  stroke="#9ca3af" 
                  tick={{ fill: "#9ca3af", fontSize: 11 }} 
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                  }}
                  formatter={(value: any) => `$${Number(value).toLocaleString()}`}
                />
                <Line type="monotone" dataKey="bb_upper" stroke="#ef4444" strokeWidth={1} dot={false} strokeDasharray="3 3" name="Upper" isAnimationActive={false} />
                <Line type="monotone" dataKey="bb_middle" stroke="#f7931a" strokeWidth={2} dot={false} name="Middle (SMA 20)" isAnimationActive={false} />
                <Line type="monotone" dataKey="bb_lower" stroke="#22c55e" strokeWidth={1} dot={false} strokeDasharray="3 3" name="Lower" isAnimationActive={false} />
                <Line type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2} dot={false} name="Price" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </DashboardPageLayout>
  )
}

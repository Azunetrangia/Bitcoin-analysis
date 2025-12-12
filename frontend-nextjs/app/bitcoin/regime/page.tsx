"use client"

import type { Metadata } from "next"
import { useState, useEffect } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import { Breadcrumb } from "@/components/dashboard/breadcrumb"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import TrendingIcon from "@/components/icons/trending"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  BarChart,
  Bar,
} from "recharts"
import { format } from "date-fns"

interface RegimeData {
  date: string
  timestamp: string
  regime: number
  regime_name: string
  regime_color: string
  close: number
  volatility: number | null
}

interface RegimeStats {
  total_periods: number
  distribution: Record<string, { count: number; percentage: number; color: string }>
  current_regime: string
  current_regime_color: string
}

export default function RegimeDetection() {
  const [dateRange, setDateRange] = useState("7D")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RegimeData[]>([])
  const [stats, setStats] = useState<RegimeStats | null>(null)

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

        const url = `http://localhost:8000/api/v1/analysis/regimes?symbol=BTCUSDT&interval=1h&start=${start.toISOString()}&end=${end.toISOString()}`
        
        const response = await fetch(url)
        if (!response.ok) throw new Error("Failed to fetch regime data")

        const json = await response.json()
        const regimes = json.regimes || []
        const regimeStats = json.stats || {}

        const transformed = regimes.map((item: any, idx: number) => ({
          date: format(new Date(item.timestamp), "MMM d HH:mm"),
          timestamp: item.timestamp,
          regime: item.regime,
          regime_name: item.regime_name,
          regime_color: item.regime_color,
          close: item.close,
          volatility: item.volatility,
          x: idx, // For scatter plot
        }))

        // Limit data points for scatter chart performance (max 500 points)
        const limit = 500
        const sampledData = transformed.length > limit
          ? transformed.filter((_: any, idx: number) => idx % Math.ceil(transformed.length / limit) === 0)
          : transformed

        setData(sampledData)
        setStats(regimeStats)
      } catch (err) {
        console.error("Error fetching regime data:", err)
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
          title: "Regime Detection",
          description: "Loading market regimes...",
          icon: TrendingIcon,
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
          title: "Regime Detection",
          description: "Error loading data",
          icon: TrendingIcon,
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

  // Prepare distribution data for bar chart
  const distributionData = stats ? Object.entries(stats.distribution).map(([name, data]) => ({
    name,
    percentage: data.percentage,
    count: data.count,
    color: data.color,
  })) : []

  return (
    <DashboardPageLayout
      header={{
        title: "Regime Detection",
        description: "Market regime classification and trend analysis",
        icon: TrendingIcon,
      }}
    >
      <Breadcrumb items={[{ label: "Regime Detection" }]} />
      
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

      {/* Current Regime & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Current Regime</CardTitle>
          </CardHeader>
          <CardContent>
            <div 
              className="text-3xl font-bold mb-2"
              style={{ color: stats?.current_regime_color }}
            >
              {stats?.current_regime}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.total_periods} periods analyzed
            </p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Regime Legend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: "#22c55e" }}></div>
                <span className="text-xs">Bullish</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: "#ef4444" }}></div>
                <span className="text-xs">Bearish</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: "#6b7280" }}></div>
                <span className="text-xs">Sideways</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: "#f59e0b" }}></div>
                <span className="text-xs">High Volatility</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Regime Distribution */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Regime Distribution</CardTitle>
          <CardDescription className="text-xs">Time spent in each market regime</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {distributionData.map((regime) => (
              <div key={regime.name} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded" 
                      style={{ backgroundColor: regime.color }}
                    ></div>
                    <span className="font-medium text-foreground">{regime.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-foreground tabular-nums">
                      {regime.percentage.toFixed(1)}%
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums">
                      ({regime.count} periods)
                    </span>
                  </div>
                </div>
                <div className="relative h-8 bg-muted rounded-lg overflow-hidden">
                  <div
                    className="absolute top-0 left-0 h-full transition-all duration-500 flex items-center justify-end pr-3"
                    style={{ 
                      width: `${regime.percentage}%`,
                      backgroundColor: regime.color,
                      minWidth: regime.percentage > 5 ? 'auto' : '40px'
                    }}
                  >
                    {regime.percentage > 10 && (
                      <span className="text-xs font-bold text-white drop-shadow-sm tabular-nums">
                        {regime.percentage.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Regime Timeline */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Regime Timeline</CardTitle>
          <CardDescription className="text-xs">Market regime changes over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="x"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  label={{ value: "Time", position: "insideBottom", offset: -5, fill: "#9ca3af" }}
                  tickFormatter={(value) => {
                    const item = data[value]
                    return item ? item.date.split(" ")[0] : ""
                  }}
                  interval={Math.floor(data.length / 8)}
                />
                <YAxis
                  dataKey="close"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  label={{ value: "Price", angle: -90, position: "insideLeft", fill: "#9ca3af" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                  }}
                  formatter={(value: any, name: string, props: any) => {
                    if (name === "close") {
                      return [`$${Number(value).toLocaleString()}`, "Price"]
                    }
                    return [value, name]
                  }}
                  labelFormatter={(value) => {
                    const item = data[value as number]
                    return item ? `${item.date} - ${item.regime_name}` : ""
                  }}
                />
                <Scatter data={data} dataKey="close" isAnimationActive={false}>
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.regime_color} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Regime Summary Table */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Regime Summary</CardTitle>
          <CardDescription className="text-xs">Statistical breakdown by regime type</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {distributionData.map((regime) => (
              <div 
                key={regime.name} 
                className="flex items-center justify-between p-3 rounded-lg border"
                style={{ borderColor: regime.color + "40" }}
              >
                <div className="flex items-center gap-3">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: regime.color }}
                  ></div>
                  <span className="font-medium">{regime.name}</span>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-right">
                    <p className="text-muted-foreground text-xs">Periods</p>
                    <p className="font-bold">{regime.count}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-muted-foreground text-xs">Percentage</p>
                    <p className="font-bold">{regime.percentage.toFixed(1)}%</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </DashboardPageLayout>
  )
}

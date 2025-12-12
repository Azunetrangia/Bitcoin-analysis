"use client"

import type { Metadata } from "next"
import { useState, useEffect } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import { Breadcrumb } from "@/components/dashboard/breadcrumb"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import RiskIcon from "@/components/icons/risk"
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { format } from "date-fns"

interface RiskData {
  date: string
  timestamp: string
  close: number
  returns: number | null
  drawdown: number | null
  cumulative: number | null
}

interface RiskMetrics {
  var_95: number
  var_99: number
  sharpe_ratio: number
  max_drawdown: number
  max_drawdown_date: string | null
  volatility: number
  current_price: number
  price_change_pct: number
  total_periods: number
}

export default function RiskAnalysis() {
  const [dateRange, setDateRange] = useState("7D")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RiskData[]>([])
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null)

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

        const url = `http://localhost:8000/api/v1/analysis/risk?symbol=BTCUSDT&interval=1h&start=${start.toISOString()}&end=${end.toISOString()}`
        
        const response = await fetch(url)
        if (!response.ok) throw new Error("Failed to fetch risk metrics")

        const json = await response.json()
        const riskData = json.data || []
        const riskMetrics = json.metrics || {}

        const transformed = riskData.map((item: any) => ({
          date: format(new Date(item.timestamp), "MMM d HH:mm"),
          timestamp: item.timestamp,
          close: item.close,
          returns: item.returns,
          drawdown: item.drawdown ? item.drawdown * 100 : null,
          cumulative: item.cumulative,
        }))

        setData(transformed)
        setMetrics(riskMetrics)
      } catch (err) {
        console.error("Error fetching risk data:", err)
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
          title: "Risk Analysis",
          description: "Loading risk metrics...",
          icon: RiskIcon,
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
          title: "Risk Analysis",
          description: "Error loading data",
          icon: RiskIcon,
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

  const varColor = metrics && metrics.var_95 < -5 ? "text-red-500" : metrics && metrics.var_95 < -2 ? "text-yellow-500" : "text-green-500"
  const sharpeColor = metrics && metrics.sharpe_ratio > 1 ? "text-green-500" : metrics && metrics.sharpe_ratio > 0 ? "text-yellow-500" : "text-red-500"
  const drawdownColor = metrics && metrics.max_drawdown < -20 ? "text-red-500" : metrics && metrics.max_drawdown < -10 ? "text-yellow-500" : "text-green-500"

  return (
    <DashboardPageLayout
      header={{
        title: "Risk Analysis",
        description: "Value at Risk, Sharpe Ratio, and Drawdown metrics",
        icon: RiskIcon,
      }}
    >
      <Breadcrumb items={[{ label: "Risk Analysis" }]} />
      
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

      {/* Risk Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">VaR (95%)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${varColor}`}>
              {metrics?.var_95.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">Max expected loss (95% confidence)</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">VaR (99%)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {metrics?.var_99.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">Max expected loss (99% confidence)</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Sharpe Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${sharpeColor}`}>
              {metrics?.sharpe_ratio.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Risk-adjusted return</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Max Drawdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${drawdownColor}`}>
              {metrics?.max_drawdown.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">Peak to trough decline</p>
          </CardContent>
        </Card>
      </div>

      {/* Additional Metrics */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Risk Summary</CardTitle>
          <CardDescription className="text-xs">
            {metrics?.total_periods} periods analyzed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Current Price</p>
              <p className="text-lg font-bold text-[#f7931a]">
                ${metrics?.current_price.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Period Return</p>
              <p className={`text-lg font-bold ${metrics && metrics.price_change_pct > 0 ? 'text-green-500' : 'text-red-500'}`}>
                {metrics?.price_change_pct.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Volatility (Ann.)</p>
              <p className="text-lg font-bold">
                {metrics?.volatility.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max DD Date</p>
              <p className="text-sm font-medium">
                {metrics?.max_drawdown_date ? format(new Date(metrics.max_drawdown_date), "MMM d, HH:mm") : "N/A"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Drawdown Chart */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Drawdown Analysis</CardTitle>
          <CardDescription className="text-xs">Portfolio decline from peak</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
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
                  tickFormatter={(value) => `${value.toFixed(1)}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                  }}
                  formatter={(value: any) => [`${Number(value).toFixed(2)}%`, "Drawdown"]}
                />
                <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
                <Area 
                  type="monotone" 
                  dataKey="drawdown" 
                  stroke="#ef4444" 
                  fillOpacity={1} 
                  fill="url(#colorDrawdown)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Price Performance */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Price Performance</CardTitle>
          <CardDescription className="text-xs">Price movement over selected period</CardDescription>
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
                  formatter={(value: any) => [`$${Number(value).toLocaleString()}`, "Price"]}
                />
                <Line 
                  type="monotone" 
                  dataKey="close" 
                  stroke="#f7931a" 
                  strokeWidth={2} 
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </DashboardPageLayout>
  )
}

"use client"

import type { Metadata } from "next"
import { useState, useEffect } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardStat from "@/components/dashboard/stat"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import BitcoinIcon from "@/components/icons/bitcoin"
import ProcessorIcon from "@/components/icons/proccesor"
import BoomIcon from "@/components/icons/boom"
import AtomIcon from "@/components/icons/atom"
import CandlestickChart from "@/components/charts/CandlestickChart"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Cell,
} from "recharts"
import { bitcoinAPI, type CandleData } from "@/lib/bitcoin-api"
import { format } from "date-fns"

interface ChartData {
  date: string
  timestamp: string
  price: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  volumeMA?: number
  volumeColor?: string
  ma20?: number
  ma50?: number
  ma200?: number
}

const iconMap = {
  bitcoin: BitcoinIcon,
  proccesor: ProcessorIcon,
  boom: BoomIcon,
  atom: AtomIcon,
}

export default function BitcoinMarketOverview() {
  const [dateRange, setDateRange] = useState("30D")
  const [showVolume, setShowVolume] = useState(true)
  const [customStartDate, setCustomStartDate] = useState("")
  const [customEndDate, setCustomEndDate] = useState("")
  const [useCustomDates, setUseCustomDates] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartData, setChartData] = useState<ChartData[]>([])
  const [marketStats, setMarketStats] = useState<any>(null)

  // Calculate MAs
  const calculateMovingAverage = (data: ChartData[], period: number): number[] => {
    const mas: number[] = []
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        mas.push(NaN)
      } else {
        const sum = data.slice(i - period + 1, i + 1).reduce((acc, d) => acc + d.close, 0)
        mas.push(sum / period)
      }
    }
    return mas
  }

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        let limit = 720 // default 30 days
        let startDate: string | undefined
        let endDate: string | undefined

        if (dateRange.startsWith("custom-")) {
          // Parse custom date range: format is "custom-YYYY-MM-DD-YYYY-MM-DD"
          const dateStr = dateRange.replace("custom-", "")
          const dates = dateStr.split("-")
          
          // dates should be [YYYY, MM, DD, YYYY, MM, DD]
          if (dates.length === 6) {
            startDate = `${dates[0]}-${dates[1]}-${dates[2]}`
            endDate = `${dates[3]}-${dates[4]}-${dates[5]}`
            
            console.log("Parsed custom dates:", { startDate, endDate })
            
            const start = new Date(startDate)
            const end = new Date(endDate)
            const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
            limit = Math.min(days * 24 + 24, 5000) // +24 to ensure we get full range
          }
        } else {
          // Use predefined ranges - get LATEST data
          const daysMap: Record<string, number> = { "7D": 7, "30D": 30, "90D": 90 }
          const days = daysMap[dateRange] || 30
          limit = days * 24
          // Don't set startDate/endDate to get latest data
        }

        console.log("Fetching market data:", {
          symbol: "BTCUSDT",
          interval: "1h",
          limit,
          startDate,
          endDate,
          dateRange
        })

        // Fetch market data - get LATEST data by not specifying dates
        const candles = await bitcoinAPI.getCandleData(
          "BTCUSDT",
          "1h",
          startDate,
          endDate,
          limit
        )

        console.log("Received candles:", candles?.length)

        if (!candles || candles.length === 0) {
          throw new Error("No data available for the selected period")
        }

        // Transform to chart data
        const transformed: ChartData[] = candles.map((candle) => ({
          date: format(new Date(candle.timestamp), "MMM d HH:mm"),
          timestamp: candle.timestamp,
          price: candle.close,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: candle.volume,
        }))

        // Calculate MAs
        if (transformed.length >= 20) {
          const ma20 = calculateMovingAverage(transformed, 20)
          transformed.forEach((d, i) => {
            d.ma20 = ma20[i]
          })
        }

        if (transformed.length >= 50) {
          const ma50 = calculateMovingAverage(transformed, 50)
          transformed.forEach((d, i) => {
            d.ma50 = ma50[i]
          })
        }

        if (transformed.length >= 200) {
          const ma200 = calculateMovingAverage(transformed, 200)
          transformed.forEach((d, i) => {
            d.ma200 = ma200[i]
          })
        }

        // Calculate Volume MA (20 period) for coloring
        if (transformed.length >= 20) {
          const volumeMA = []
          for (let i = 0; i < transformed.length; i++) {
            if (i < 19) {
              volumeMA.push(NaN)
            } else {
              const sum = transformed.slice(i - 19, i + 1).reduce((acc, d) => acc + d.volume, 0)
              volumeMA.push(sum / 20)
            }
          }
          transformed.forEach((d, i) => {
            d.volumeMA = volumeMA[i]
            // Green if above MA, Red if below
            d.volumeColor = !isNaN(volumeMA[i]) && d.volume > volumeMA[i] ? "#22c55e" : "#ef4444"
          })
        }

        setChartData(transformed)

        // Calculate 24h metrics (like Streamlit logic)
        const latest = transformed[transformed.length - 1]
        const latestTime = new Date(latest.timestamp)
        const time24hAgo = new Date(latestTime.getTime() - 24 * 60 * 60 * 1000)
        
        // Filter data for last 24 hours
        const last24h = transformed.filter(d => new Date(d.timestamp) >= time24hAgo)
        
        let open24h = latest.open
        let high24h = latest.high
        let low24h = latest.low
        let volume24h = latest.volume * latest.close
        
        if (last24h.length > 0) {
          open24h = last24h[0].open
          high24h = Math.max(...last24h.map(d => d.high))
          low24h = Math.min(...last24h.map(d => d.low))
          volume24h = last24h.reduce((sum, d) => sum + d.volume, 0) * latest.close
        }
        
        const priceChange = latest.close - open24h
        const priceChangePct = (priceChange / open24h) * 100
        
        // Calculate volatility (annualized std dev of returns)
        const returns = transformed.slice(-24).map((d, i, arr) => 
          i > 0 ? (d.close - arr[i-1].close) / arr[i-1].close : 0
        ).filter((_, i) => i > 0)
        
        const meanReturn = returns.reduce((a, b) => a + b, 0) / returns.length
        const variance = returns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) / returns.length
        const volatility = Math.sqrt(variance * 365 * 24) * 100 // Annualized
        
        setMarketStats({
          currentPrice: latest.close,
          change24h: priceChange,
          changePercent24h: priceChangePct,
          high24h,
          low24h,
          volume24h,
          volatility,
        })
      } catch (err) {
        console.error("Error fetching data:", err)
        setError(err instanceof Error ? err.message : "Failed to load data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [dateRange])

  // Calculate statistics
  const calculateStats = () => {
    if (chartData.length === 0) return null

    const closes = chartData.map((d) => d.close)
    const volumes = chartData.map((d) => d.volume)

    const mean = closes.reduce((a, b) => a + b, 0) / closes.length
    const sortedCloses = [...closes].sort((a, b) => a - b)
    const median = sortedCloses[Math.floor(sortedCloses.length / 2)]
    const stdDev = Math.sqrt(
      closes.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / closes.length
    )

    const volMean = volumes.reduce((a, b) => a + b, 0) / volumes.length
    const sortedVols = [...volumes].sort((a, b) => a - b)
    const volMedian = sortedVols[Math.floor(sortedVols.length / 2)]
    const volStdDev = Math.sqrt(
      volumes.reduce((sum, val) => sum + Math.pow(val - volMean, 2), 0) / volumes.length
    )

    return {
      price: {
        mean,
        stdDev,
        min: Math.min(...closes),
        max: Math.max(...closes),
        median,
      },
      volume: {
        mean: volMean,
        stdDev: volStdDev,
        min: Math.min(...volumes),
        max: Math.max(...volumes),
        median: volMedian,
      },
    }
  }

  const stats = calculateStats()

  // Mock stats for display
  const mockStats = marketStats
    ? [
        {
          label: "Current Price",
          value: `$${marketStats.currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          description: "BTC/USDT",
          icon: "bitcoin",
          tag: `${marketStats.changePercent24h >= 0 ? "+" : ""}${marketStats.changePercent24h.toFixed(1)}%`,
          intent: (marketStats.changePercent24h >= 0 ? "positive" : "negative") as const,
          direction: (marketStats.changePercent24h >= 0 ? "up" : "down") as const,
        },
        {
          label: "24h Volume",
          value: `$${(marketStats.volume24h / 1e9).toFixed(1)}B`,
          description: "Trading volume",
          icon: "proccesor",
          tag: "+12.3%",
          intent: "positive" as const,
          direction: "up" as const,
        },
        {
          label: "Volatility",
          value: `${marketStats.volatility.toFixed(1)}%`,
          description: "Daily annualized",
          icon: "boom",
          tag: marketStats.volatility > 5 ? "Elevated" : marketStats.volatility > 2 ? "Normal" : "Low",
          intent: (marketStats.volatility > 5 ? "negative" : "positive") as const,
          direction: "up" as const,
        },
        {
          label: "24h High/Low",
          value: `$${marketStats.high24h.toLocaleString()}`,
          description: `Low: $${marketStats.low24h.toLocaleString()}`,
          icon: "atom",
          tag: `Range ${((marketStats.high24h - marketStats.low24h) / marketStats.low24h * 100).toFixed(1)}%`,
          intent: "neutral" as const,
          direction: "up" as const,
        },
      ]
    : []

  const priceStats =
    chartData.length > 0 && marketStats
      ? [
          { label: "Current Price", value: `$${marketStats.currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: "text-foreground" },
          { label: "24h High", value: `$${marketStats.high24h.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: "text-green-500" },
          { label: "24h Low", value: `$${marketStats.low24h.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: "text-red-500" },
          {
            label: "24h Change",
            value: `${marketStats.change24h >= 0 ? "+" : ""}$${Math.abs(marketStats.change24h).toLocaleString(undefined, { minimumFractionDigits: 2 })} (${marketStats.changePercent24h >= 0 ? "+" : ""}${marketStats.changePercent24h.toFixed(1)}%)`,
            color: marketStats.changePercent24h >= 0 ? "text-green-500" : "text-red-500"
          },
        ]
      : []

  const volumeStats =
    chartData.length > 0 && marketStats
      ? [
          { label: "24h Volume", value: `$${(marketStats.volume24h / 1e9).toFixed(1)}B` },
          { label: "Volume Change", value: "+12.3%" },
          {
            label: "Avg Volume",
            value: `${(
              chartData.reduce((sum, d) => sum + d.volume, 0) / chartData.length
            ).toFixed(2)} BTC`,
          },
          { label: "Number of Trades", value: `${chartData.length.toLocaleString()}` },
        ]
      : []

  // Loading skeleton
  if (isLoading) {
    return (
      <DashboardPageLayout
        header={{
          title: "Market Overview",
          description: "Loading market data...",
          icon: BitcoinIcon,
        }}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-96 mb-6" />
      </DashboardPageLayout>
    )
  }

  // Error state
  if (error) {
    return (
      <DashboardPageLayout
        header={{
          title: "Market Overview",
          description: "Error loading data",
          icon: BitcoinIcon,
        }}
      >
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Failed to Load Data</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <p className="text-xs text-muted-foreground">
              Make sure the FastAPI backend is running on http://localhost:8000
            </p>
            <Button onClick={() => window.location.reload()} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </DashboardPageLayout>
    )
  }

  return (
    <DashboardPageLayout
      header={{
        title: "Market Overview",
        description: "Real-time Bitcoin market data with interactive charts",
        icon: BitcoinIcon,
      }}
    >
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {mockStats.map((stat, index) => (
          <DashboardStat
            key={index}
            label={stat.label}
            value={stat.value}
            description={stat.description}
            icon={iconMap[stat.icon as keyof typeof iconMap]}
            tag={stat.tag}
            intent={stat.intent}
            direction={stat.direction}
          />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* Left Column - Price Statistics */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Price Statistics</CardTitle>
            <CardDescription className="text-xs">24-hour metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {priceStats.map((stat, idx) => (
                <div key={idx} className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">{stat.label}</span>
                  <span className={`text-sm font-medium ${stat.color || ""}`}>{stat.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Right Column - Filters */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Filters</CardTitle>
            <CardDescription className="text-xs">
              {chartData.length.toLocaleString()} candles | {chartData[0]?.timestamp ? format(new Date(chartData[0].timestamp), "MMM d") : ""} - {chartData[chartData.length - 1]?.timestamp ? format(new Date(chartData[chartData.length - 1].timestamp), "MMM d, yyyy") : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Time Range & Custom Date in same row */}
            <div className="grid grid-cols-2 gap-3">
              {/* Quick Select */}
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Time Range:</label>
                <div className="inline-flex gap-1 p-1 bg-muted rounded-md">
                  {["7D", "30D", "90D"].map((range) => (
                    <button
                      key={range}
                      onClick={() => {
                        setDateRange(range)
                        setUseCustomDates(false)
                        setCustomStartDate("")
                        setCustomEndDate("")
                      }}
                      className={`px-3 py-1 text-xs rounded transition-colors ${
                        dateRange === range && !useCustomDates
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-background"
                      }`}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Date Toggle */}
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Custom Range:</label>
                {!useCustomDates ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setUseCustomDates(true)}
                    className="w-full text-xs h-8"
                  >
                    📅 Select Dates
                  </Button>
                ) : (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => {
                      setUseCustomDates(false)
                      setCustomStartDate("")
                      setCustomEndDate("")
                    }}
                    className="w-full text-xs h-8"
                  >
                    ✕ Cancel
                  </Button>
                )}
              </div>
            </div>

            {/* Custom Date Inputs (when enabled) */}
            {useCustomDates && (
              <div className="border border-border rounded-md p-3 bg-muted/30 space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">From:</label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => setCustomStartDate(e.target.value)}
                      min="2020-01-01"
                      max={customEndDate || "2025-12-31"}
                      className="w-full px-3 py-2 text-sm bg-background border border-border rounded cursor-pointer hover:border-[#f7931a]/50 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">To:</label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => setCustomEndDate(e.target.value)}
                      min={customStartDate || "2020-01-01"}
                      max="2025-12-31"
                      className="w-full px-3 py-2 text-sm bg-background border border-border rounded cursor-pointer hover:border-[#f7931a]/50 transition-colors"
                    />
                  </div>
                </div>
                {customStartDate && customEndDate && (
                  <Button
                    onClick={() => {
                      // Close custom date inputs and trigger fetch
                      const newDateRange = `custom-${customStartDate}-${customEndDate}`
                      console.log("Apply button clicked:", { customStartDate, customEndDate, newDateRange })
                      setDateRange(newDateRange)
                      setUseCustomDates(false)
                    }}
                    size="sm"
                    className="w-full text-xs h-8 font-medium"
                  >
                    Apply Custom Range
                  </Button>
                )}
              </div>
            )}

            {/* Show Volume */}
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={showVolume}
                onChange={(e) => setShowVolume(e.target.checked)}
                className="rounded h-3.5 w-3.5"
              />
              Show Volume
            </label>
          </CardContent>
        </Card>
      </div>

      {/* Main Price Chart - OHLC */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">OHLC Candlestick Chart</CardTitle>
          <CardDescription className="text-xs">Price action with volume indicator</CardDescription>
        </CardHeader>
        <CardContent>
          <CandlestickChart data={chartData} showVolume={showVolume} />
        </CardContent>
      </Card>

      {/* Moving Averages */}
      {chartData.length >= 20 && (
        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Price with Moving Averages</CardTitle>
            <CardDescription className="text-xs">
              {(() => {
                const mas = []
                if (chartData.some(d => d.ma20 && !isNaN(d.ma20))) mas.push("MA20 (cyan)")
                if (chartData.some(d => d.ma50 && !isNaN(d.ma50))) mas.push("MA50 (green)")
                if (chartData.some(d => d.ma200 && !isNaN(d.ma200))) mas.push("MA200 (red dashed)")
                return mas.length > 0 ? mas.join(", ") : "Moving averages"
              })()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* MA Signals */}
            <div className="space-y-2 mb-4">
              {chartData[chartData.length - 1]?.ma20 && !isNaN(chartData[chartData.length - 1].ma20!) && (
                <div
                  className={`p-3 rounded text-sm font-medium ${
                    chartData[chartData.length - 1].close > chartData[chartData.length - 1].ma20!
                      ? "bg-green-500/10 border border-green-500/30 text-green-600"
                      : "bg-orange-500/10 border border-orange-500/30 text-orange-600"
                  }`}
                >
                  {chartData[chartData.length - 1].close > chartData[chartData.length - 1].ma20!
                    ? `✅ Price above MA20 ($${chartData[chartData.length - 1].ma20!.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}) - Short-term bullish`
                    : `⚠️ Price below MA20 ($${chartData[chartData.length - 1].ma20!.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}) - Short-term bearish`}
                </div>
              )}
              {chartData[chartData.length - 1]?.ma50 && !isNaN(chartData[chartData.length - 1].ma50!) && (
                <div
                  className={`p-3 rounded text-sm font-medium ${
                    chartData[chartData.length - 1].close > chartData[chartData.length - 1].ma50!
                      ? "bg-green-500/10 border border-green-500/30 text-green-600"
                      : "bg-orange-500/10 border border-orange-500/30 text-orange-600"
                  }`}
                >
                  {chartData[chartData.length - 1].close > chartData[chartData.length - 1].ma50!
                    ? `✅ Price above MA50 ($${chartData[chartData.length - 1].ma50!.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}) - Mid-term bullish`
                    : `⚠️ Price below MA50 ($${chartData[chartData.length - 1].ma50!.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}) - Mid-term bearish`}
                </div>
              )}
            </div>

            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9ca3af" 
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    interval={Math.floor(chartData.length / 8)}
                  />
                  <YAxis 
                    stroke="#9ca3af" 
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1f2937",
                      border: "1px solid #374151",
                      color: "#f3f4f6",
                      borderRadius: "6px"
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ paddingTop: '10px' }}
                    iconType="line"
                  />
                  <Line type="monotone" dataKey="close" stroke="#f7931a" strokeWidth={3} dot={false} name="BTC Price" isAnimationActive={false} />
                  {chartData.some(d => d.ma20 && !isNaN(d.ma20)) && (
                    <Line
                      type="monotone"
                      dataKey="ma20"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      dot={false}
                      name="MA20"
                      isAnimationActive={false}
                      connectNulls={false}
                      opacity={0.9}
                    />
                  )}
                  {chartData.some(d => d.ma50 && !isNaN(d.ma50)) && (
                    <Line
                      type="monotone"
                      dataKey="ma50"
                      stroke="#22c55e"
                      strokeWidth={2.5}
                      dot={false}
                      name="MA50"
                      isAnimationActive={false}
                      connectNulls={false}
                      opacity={0.9}
                    />
                  )}
                  {chartData.some(d => d.ma200 && !isNaN(d.ma200)) && (
                    <Line
                      type="monotone"
                      dataKey="ma200"
                      stroke="#ef4444"
                      strokeWidth={2.5}
                      dot={false}
                      name="MA200"
                      strokeDasharray="10 5"
                      isAnimationActive={false}
                      connectNulls={false}
                      opacity={0.8}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Volume Analysis */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Volume Analysis</CardTitle>
          <CardDescription className="text-xs">Volume bars colored by comparison to 20-period MA (green = above average, red = below)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.slice(-50)} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    color: "#f3f4f6",
                    borderRadius: "6px"
                  }}
                />
                <Bar dataKey="volume" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {chartData.slice(-50).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.volumeColor || "#4facfe"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            {volumeStats.map((stat, index) => (
              <div key={index} className="border border-border rounded-lg p-4">
                <p className="text-xs text-muted-foreground mb-1">{stat.label}</p>
                <p className="text-sm font-semibold">{stat.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Statistical Summary */}
      {stats && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Statistical Summary</CardTitle>
            <CardDescription className="text-xs">
              Statistics for selected period: {chartData.length} days ({format(new Date(chartData[0]?.timestamp || ""), "MMM d")} - {format(new Date(chartData[chartData.length - 1]?.timestamp || ""), "MMM d, yyyy")})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-bold mb-4">Close Price Statistics</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {[
                    { label: "Mean", value: `$${stats.price.mean.toLocaleString(undefined, {minimumFractionDigits: 2})}` },
                    { label: "Std Dev", value: `$${stats.price.stdDev.toLocaleString(undefined, {minimumFractionDigits: 2})}` },
                    { label: "Min", value: `$${stats.price.min.toLocaleString(undefined, {minimumFractionDigits: 2})}` },
                    { label: "Max", value: `$${stats.price.max.toLocaleString(undefined, {minimumFractionDigits: 2})}` },
                    { label: "Median", value: `$${stats.price.median.toLocaleString(undefined, {minimumFractionDigits: 2})}` },
                  ].map((stat, index) => (
                    <div key={index} className="bg-muted p-4 rounded">
                      <p className="text-base text-muted-foreground mb-2 font-medium">{stat.label}</p>
                      <p className="text-lg font-bold">{stat.value}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-lg font-bold mb-4">Volume Statistics</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {[
                    { label: "Mean", value: `${stats.volume.mean.toFixed(2)} BTC` },
                    { label: "Std Dev", value: `${stats.volume.stdDev.toFixed(2)} BTC` },
                    { label: "Min", value: `${stats.volume.min.toFixed(2)} BTC` },
                    { label: "Max", value: `${stats.volume.max.toFixed(2)} BTC` },
                    { label: "Median", value: `${stats.volume.median.toFixed(2)} BTC` },
                  ].map((stat, index) => (
                    <div key={index} className="bg-muted p-4 rounded">
                      <p className="text-base text-muted-foreground mb-2 font-medium">{stat.label}</p>
                      <p className="text-lg font-bold">{stat.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </DashboardPageLayout>
  )
}

"use client"

import { useState } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardStat from "@/components/dashboard/stat"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import BitcoinIcon from "@/components/icons/bitcoin"
import ProcessorIcon from "@/components/icons/proccesor"
import BoomIcon from "@/components/icons/boom"
import AtomIcon from "@/components/icons/atom"
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
} from "recharts"

// Mock data for charts
const mockChartData = [
  { date: "Jan 1", price: 42000, volume: 28.5, ma20: 41500, ma50: 41000, ma200: 40800 },
  { date: "Jan 2", price: 42500, volume: 32.1, ma20: 41700, ma50: 41050, ma200: 40850 },
  { date: "Jan 3", price: 43000, volume: 35.4, ma20: 42000, ma50: 41100, ma200: 40900 },
  { date: "Jan 4", price: 44200, volume: 29.8, ma20: 42500, ma50: 41200, ma200: 40950 },
  { date: "Jan 5", price: 44800, volume: 38.2, ma20: 43000, ma50: 41350, ma200: 41000 },
  { date: "Jan 6", price: 45230, volume: 42.1, ma20: 43500, ma50: 41500, ma200: 41050 },
  { date: "Jan 7", price: 45100, volume: 31.5, ma20: 43800, ma50: 41600, ma200: 41100 },
]

const volumeStats = [
  { label: "24h Volume", value: "$28.5B" },
  { label: "Volume Change", value: "+12.3%" },
  { label: "Avg Volume", value: "$1.2M" },
  { label: "Number of Trades", value: "2,450K" },
]

const priceStats = [
  { label: "Current Price", value: "$45,230.50" },
  { label: "24h High", value: "$46,100.00" },
  { label: "24h Low", value: "$44,500.00" },
  { label: "24h Change", value: "+$3,230.50 (+7.7%)" },
]

export default function BitcoinMarketOverview() {
  const [dateRange, setDateRange] = useState("30D")
  const [showVolume, setShowVolume] = useState(true)

  const mockStats = [
    {
      label: "Current Price",
      value: "$45,230.50",
      description: "BTC/USDT",
      icon: "bitcoin",
      tag: "+7.7%",
      intent: "positive" as const,
      direction: "up" as const,
    },
    {
      label: "24h Volume",
      value: "$28.5B",
      description: "Trading volume",
      icon: "proccesor",
      tag: "+12.3%",
      intent: "positive" as const,
      direction: "up" as const,
    },
    {
      label: "Volatility",
      value: "18.5%",
      description: "Daily annualized",
      icon: "boom",
      tag: "Elevated",
      intent: "negative" as const,
      direction: "up" as const,
    },
    {
      label: "Sharpe Ratio",
      value: "1.24",
      description: "24-hour window",
      icon: "atom",
      tag: "Good",
      intent: "positive" as const,
      direction: "up" as const,
    },
  ]

  const iconMap = {
    bitcoin: BitcoinIcon,
    proccesor: ProcessorIcon,
    boom: BoomIcon,
    atom: AtomIcon,
  }

  return (
    <DashboardPageLayout
      header={{
        title: "Market Overview",
        description: "Real-time Bitcoin market data with interactive charts",
        icon: BitcoinIcon,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
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

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Filters</CardTitle>
              <CardDescription>Loaded 7,234 candles from Jan 1 - Jan 7</CardDescription>
            </div>
            <div className="flex gap-2">
              {["7D", "30D", "90D"].map((range) => (
                <Button
                  key={range}
                  variant={dateRange === range ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDateRange(range)}
                  className="text-xs"
                >
                  {range}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showVolume}
              onChange={(e) => setShowVolume(e.target.checked)}
              className="rounded"
            />
            Show Volume
          </label>
        </CardContent>
      </Card>

      {/* Price Statistics */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Price Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {priceStats.map((stat, index) => (
              <div key={index} className="border border-border rounded-lg p-4">
                <p className="text-xs text-muted-foreground mb-1">{stat.label}</p>
                <p className="text-base font-semibold">{stat.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Candlestick Chart */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>OHLC Candlestick Chart</CardTitle>
          <CardDescription>Price action with volume indicator</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={mockChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#f7931a"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                  yAxisId="left"
                />
                {showVolume && <Bar dataKey="volume" fill="#4facfe" opacity={0.3} yAxisId="right" />}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Moving Averages */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Price with Moving Averages</CardTitle>
          <CardDescription>20-day (orange), 50-day (green), 200-day (purple) moving averages</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 mb-4">
            <div className="p-3 bg-success/10 border border-success/20 rounded text-sm text-success">
              Price above MA20 ($43,800) - Short-term bullish
            </div>
            <div className="p-3 bg-success/10 border border-success/20 rounded text-sm text-success">
              Price above MA50 ($41,600) - Mid-term bullish
            </div>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                  }}
                />
                <Line type="monotone" dataKey="price" stroke="#f7931a" strokeWidth={2.5} dot={false} name="Price" />
                <Line
                  type="monotone"
                  dataKey="ma20"
                  stroke="#ff9500"
                  strokeWidth={1.5}
                  dot={false}
                  name="MA20"
                  strokeDasharray="5 5"
                />
                <Line
                  type="monotone"
                  dataKey="ma50"
                  stroke="#22c55e"
                  strokeWidth={1.5}
                  dot={false}
                  name="MA50"
                  strokeDasharray="5 5"
                />
                <Line
                  type="monotone"
                  dataKey="ma200"
                  stroke="#a855f7"
                  strokeWidth={1.5}
                  dot={false}
                  name="MA200"
                  strokeDasharray="5 5"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Volume Analysis */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Volume Analysis</CardTitle>
          <CardDescription>Volume bars colored by comparison to 20-period MA</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 mb-4">
            <div className="p-3 bg-warning/10 border border-warning/20 rounded text-sm text-warning">
              High volume: 42.1B average
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockChartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                  }}
                />
                <Bar dataKey="volume" fill="#4facfe" radius={[4, 4, 0, 0]} isAnimationActive={false} />
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
      <Card>
        <CardHeader>
          <CardTitle>Statistical Summary</CardTitle>
          <CardDescription>Statistics for selected period: 7 days (Jan 1 - Jan 7)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-semibold mb-3">Close Price Statistics</h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: "Mean", value: "$43,847.50" },
                  { label: "Std Dev", value: "$1,123.45" },
                  { label: "Min", value: "$42,000.00" },
                  { label: "Max", value: "$45,230.50" },
                  { label: "Median", value: "$44,200.00" },
                ].map((stat, index) => (
                  <div key={index} className="bg-muted p-3 rounded">
                    <p className="text-xs text-muted-foreground mb-1">{stat.label}</p>
                    <p className="text-xs font-semibold">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-3">Volume Statistics</h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: "Mean", value: "34.23B" },
                  { label: "Std Dev", value: "5.12B" },
                  { label: "Min", value: "28.50B" },
                  { label: "Max", value: "42.10B" },
                  { label: "Median", value: "32.80B" },
                ].map((stat, index) => (
                  <div key={index} className="bg-muted p-3 rounded">
                    <p className="text-xs text-muted-foreground mb-1">{stat.label}</p>
                    <p className="text-xs font-semibold">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </DashboardPageLayout>
  )
}

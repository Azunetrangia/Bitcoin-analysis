"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import DashboardPageLayout from "@/components/dashboard/layout"
import DashboardStat from "@/components/dashboard/stat"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import BitcoinIcon from "@/components/icons/bitcoin"
import { TradingSignals } from "@/components/bitcoin/trading-signals"
import ProcessorIcon from "@/components/icons/proccesor"
import BoomIcon from "@/components/icons/boom"
import AtomIcon from "@/components/icons/atom"
import { ArrowRight, TrendingUp, BarChart3, Activity, AlertTriangle } from "lucide-react"





export default function BitcoinOverview() {
  const router = useRouter()
  const [livePrice, setLivePrice] = useState<number | null>(null)
  const [priceChange24h, setPriceChange24h] = useState<number>(0)
  const [high24h, setHigh24h] = useState<number | null>(null)
  const [low24h, setLow24h] = useState<number | null>(null)
  const [volume24h, setVolume24h] = useState<number | null>(null)
  const [volumeUSDT, setVolumeUSDT] = useState<number | null>(null)
  const [volatility, setVolatility] = useState<number | null>(null)
  const [sharpeRatio, setSharpeRatio] = useState<number | null>(null)

  // Fetch live price from Binance API
  useEffect(() => {
    const fetchLivePrice = async () => {
      try {
        const response = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        const data = await response.json()
        setLivePrice(parseFloat(data.lastPrice))
        setPriceChange24h(parseFloat(data.priceChangePercent))
        setHigh24h(parseFloat(data.highPrice))
        setLow24h(parseFloat(data.lowPrice))
        setVolume24h(parseFloat(data.volume))
        setVolumeUSDT(parseFloat(data.quoteVolume))
        
        // Calculate volatility from 24h price range
        const high = parseFloat(data.highPrice)
        const low = parseFloat(data.lowPrice)
        const avgPrice = (high + low) / 2
        const range = high - low
        // Annualized volatility estimate: (range / avgPrice) * sqrt(365)
        const dailyVol = (range / avgPrice) * 100
        const annualizedVol = dailyVol * Math.sqrt(365)
        setVolatility(annualizedVol)
        
        // Calculate simple Sharpe Ratio
        // Sharpe = (Return - RiskFreeRate) / Volatility
        // Assuming risk-free rate ≈ 0 for crypto
        const dailyReturn = parseFloat(data.priceChangePercent)
        const annualizedReturn = dailyReturn * 365
        const sharpe = dailyVol > 0 ? annualizedReturn / annualizedVol : 0
        setSharpeRatio(sharpe)
      } catch (error) {
        console.error('Error fetching live price:', error)
      }
    }

    fetchLivePrice()
    const interval = setInterval(fetchLivePrice, 10000) // Update every 10 seconds

    return () => clearInterval(interval)
  }, [])

  const quickStats = [
    {
      label: "Current Price",
      value: livePrice ? `$${livePrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Loading...",
      description: "BTC/USDT",
      icon: "bitcoin",
      tag: livePrice ? `${priceChange24h >= 0 ? '+' : ''}${priceChange24h.toFixed(2)}%` : "...",
      intent: (priceChange24h >= 0 ? "positive" : "negative") as const,
      direction: (priceChange24h >= 0 ? "up" : "down") as const,
    },
    {
      label: "24h Volume",
      value: volumeUSDT ? `$${(volumeUSDT / 1e9).toFixed(1)}B` : "Loading...",
      description: "Trading volume",
      icon: "proccesor",
      tag: volumeUSDT && volume24h ? `${volume24h.toLocaleString(undefined, { maximumFractionDigits: 0 })} BTC` : "...",
      intent: "positive" as const,
      direction: "up" as const,
    },
    {
      label: "Volatility",
      value: volatility ? `${volatility.toFixed(1)}%` : "Loading...",
      description: "Daily annualized",
      icon: "boom",
      tag: volatility ? (volatility > 50 ? "Elevated" : volatility > 30 ? "Normal" : "Low") : "...",
      intent: (volatility && volatility > 50 ? "negative" : "positive") as const,
      direction: "up" as const,
    },
    {
      label: "Sharpe Ratio",
      value: sharpeRatio !== null ? sharpeRatio.toFixed(2) : "Loading...",
      description: "24-hour window",
      icon: "atom",
      tag: sharpeRatio !== null ? (sharpeRatio > 1 ? "Good" : sharpeRatio > 0 ? "Fair" : "Poor") : "...",
      intent: (sharpeRatio !== null && sharpeRatio > 1 ? "positive" : "neutral") as const,
      direction: (sharpeRatio !== null && sharpeRatio > 0 ? "up" : "down") as const,
    },
  ]

  const iconMap = {
    bitcoin: BitcoinIcon,
    proccesor: ProcessorIcon,
    boom: BoomIcon,
    atom: AtomIcon,
  }

  // Quick navigation sections
  const analysisPages = [
    {
      title: "Market Analysis",
      description: "Detailed OHLC charts, moving averages, and volume analysis",
      icon: BarChart3,
      href: "/bitcoin/market",
      color: "text-blue-500"
    },
    {
      title: "Technical Indicators",
      description: "RSI, MACD, Bollinger Bands, and advanced technical analysis",
      icon: TrendingUp,
      href: "/bitcoin/technical",
      color: "text-green-500"
    },
    {
      title: "Risk Metrics",
      description: "VaR, CVaR, volatility analysis, and risk assessment",
      icon: AlertTriangle,
      href: "/bitcoin/risk",
      color: "text-orange-500"
    },
    {
      title: "Regime Classification",
      description: "HMM-based market regime detection (Bull/Bear/Sideways)",
      icon: Activity,
      href: "/bitcoin/regime",
      color: "text-purple-500"
    }
  ]

  return (
    <DashboardPageLayout
      header={{
        title: "Bitcoin Dashboard",
        description: "Real-time trading signals and market intelligence",
        icon: BitcoinIcon,
      }}
    >
      {/* Trading Signals Section */}
      <div className="mb-6">
        <TradingSignals />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {quickStats.map((stat, index) => (
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

      {/* Market Summary Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Market Summary</CardTitle>
          <CardDescription>24-hour Bitcoin market snapshot</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Current Price</p>
              <p className="text-lg font-semibold">
                {livePrice ? `$${livePrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Loading..."}
              </p>
            </div>
            <div className="p-4 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">24h High</p>
              <p className="text-lg font-semibold">
                {high24h ? `$${high24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Loading..."}
              </p>
            </div>
            <div className="p-4 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">24h Low</p>
              <p className="text-lg font-semibold">
                {low24h ? `$${low24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Loading..."}
              </p>
            </div>
            <div className="p-4 border border-border rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">24h Volume</p>
              <p className="text-lg font-semibold">
                {volume24h ? `${(volume24h / 1000).toFixed(1)}K BTC` : "Loading..."}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Navigation */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4">Detailed Analysis</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {analysisPages.map((page, index) => (
            <Card key={index} className="cursor-pointer hover:bg-accent transition-colors" onClick={() => router.push(page.href)}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <page.icon className={`h-5 w-5 ${page.color}`} />
                      <h3 className="font-semibold">{page.title}</h3>
                    </div>
                    <p className="text-sm text-muted-foreground">{page.description}</p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-muted-foreground ml-4" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

    </DashboardPageLayout>
  )
}

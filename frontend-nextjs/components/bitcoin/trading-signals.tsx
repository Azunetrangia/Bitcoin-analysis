"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";

interface RegimeData {
  regime: string;
  probability: number;
  confidence: string;
}

interface KAMAData {
  value: number;
  signal: string;
  distance_pct: number;
}

interface OnchainData {
  funding_rate: string;
  market_cap_signal: string;
}

interface SignalData {
  symbol: string;
  timestamp: string;
  current_price: number;
  recommendation: string;
  confidence: string;
  composite_score: number;
  regime: RegimeData;
  kama: KAMAData;
  onchain: OnchainData;
  factors: Array<{name: string; signal: string; weight: number}>;
}

export function TradingSignals() {
  const [signals, setSignals] = useState<SignalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/v1/signals/comprehensive");
        if (!response.ok) throw new Error("Failed to fetch signals");
        const data = await response.json();
        setSignals(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchSignals();
    // Refresh every 30 seconds
    const interval = setInterval(fetchSignals, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trading Signals</CardTitle>
          <CardDescription>Loading market analysis...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error || !signals) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trading Signals</CardTitle>
          <CardDescription className="text-red-500">
            {error || "No data available"}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case "STRONG BUY":
        return "bg-green-600 text-white hover:bg-green-700";
      case "BUY":
        return "bg-green-500 text-white hover:bg-green-600";
      case "HOLD":
        return "bg-yellow-500 text-white hover:bg-yellow-600";
      case "SELL":
        return "bg-red-500 text-white hover:bg-red-600";
      case "STRONG SELL":
        return "bg-red-600 text-white hover:bg-red-700";
      default:
        return "bg-gray-500 text-white";
    }
  };

  const getRegimeIcon = (regime: string) => {
    switch (regime) {
      case "Bull":
        return <TrendingUp className="h-4 w-4" />;
      case "Bear":
        return <TrendingDown className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const getRegimeColor = (regime: string) => {
    switch (regime) {
      case "Bull":
        return "bg-green-100 text-green-800 border-green-300";
      case "Bear":
        return "bg-red-100 text-red-800 border-red-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Main Signal Card */}
      <Card className="relative overflow-hidden">
        <CardHeader className="flex items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <div className="rounded-[1.5px] bg-primary size-2" />
            Signal
          </CardTitle>
          <Activity className="size-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent className="bg-accent flex-1 pt-2 pb-3 overflow-clip relative">
          <Badge className={`${getRecommendationColor(signals.recommendation)} text-sm px-3 py-0.5 font-bold uppercase mb-2`}>
            {signals.recommendation}
          </Badge>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-semibold">{signals.confidence}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Score</span>
              <span className={`font-bold text-lg ${signals.composite_score > 0 ? "text-success" : "text-destructive"}`}>
                {signals.composite_score > 0 ? "+" : ""}{signals.composite_score}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Price</span>
              <span className="font-mono text-sm font-semibold">${signals.current_price.toLocaleString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Market Regime */}
      <Card className="relative overflow-hidden">
        <CardHeader className="flex items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <div className="rounded-[1.5px] bg-primary size-2" />
            Market Regime
          </CardTitle>
          {getRegimeIcon(signals.regime.regime)}
        </CardHeader>
        <CardContent className="bg-accent flex-1 pt-2 pb-3 overflow-clip relative">
          <CardDescription className="text-xs mb-1.5">HMM Classification</CardDescription>
          <div className="mb-2">
            <Badge className={`${signals.regime.regime === 'Bull' ? 'bg-green-500 hover:bg-green-600 text-white' : signals.regime.regime === 'Bear' ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-gray-500 hover:bg-gray-600 text-white'} flex items-center gap-1 text-sm px-3 py-0.5 uppercase`}>
              {getRegimeIcon(signals.regime.regime)}
              {signals.regime.regime}
            </Badge>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Probability</span>
              <span className="font-bold text-sm">{(signals.regime.probability * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Confidence</span>
              <span className="text-xs font-semibold bg-blue-500 text-white px-2 py-0.5 rounded">{signals.regime.confidence}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KAMA Indicator */}
      <Card className="relative overflow-hidden">
        <CardHeader className="flex items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <div className="rounded-[1.5px] bg-primary size-2" />
            KAMA Indicator
          </CardTitle>
          <TrendingUp className="size-3.5 text-muted-foreground" />
        </CardHeader>
        <CardContent className="bg-accent flex-1 pt-2 pb-3 overflow-clip relative">
          <CardDescription className="text-xs mb-1.5">Adaptive Moving Average</CardDescription>
          <div className="mb-2">
            <Badge 
              className={`text-sm px-3 py-0.5 font-bold uppercase ${
                signals.kama.signal === "BUY" || signals.kama.signal === "BULLISH" 
                  ? "bg-green-500 hover:bg-green-600 text-white" 
                  : signals.kama.signal === "SELL" || signals.kama.signal === "BEARISH"
                  ? "bg-red-500 hover:bg-red-600 text-white"
                  : "bg-gray-500 hover:bg-gray-600 text-white"
              }`}
            >
              {signals.kama.signal}
            </Badge>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">KAMA Value</span>
              <span className="font-mono font-bold text-sm">${(signals.kama.value / 1000).toFixed(1)}K</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Distance</span>
              <span className={`font-bold text-base ${signals.kama.distance_pct > 0 ? "text-success" : "text-destructive"}`}>
                {signals.kama.distance_pct > 0 ? "+" : ""}{signals.kama.distance_pct.toFixed(2)}%
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Signal Breakdown - Full Width */}
      <Card className="md:col-span-2 lg:col-span-4">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2.5">
            <div className="rounded-[1.5px] bg-primary size-2.5" />
            Signal Breakdown
          </CardTitle>
          <CardDescription>Contributing factors to recommendation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {signals.factors.map((factor, idx) => (
              <div 
                key={idx} 
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent/50 transition-colors"
              >
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-medium">{factor.name}</span>
                  <span className="text-xs text-muted-foreground">{factor.signal}</span>
                </div>
                <Badge 
                  className={`text-base font-bold px-2.5 py-0.5 ${
                    factor.weight > 0 
                      ? "bg-green-500 hover:bg-green-600 text-white" 
                      : factor.weight < 0 
                      ? "bg-red-500 hover:bg-red-600 text-white"
                      : "bg-gray-500 hover:bg-gray-600 text-white"
                  }`}
                >
                  {factor.weight > 0 ? "+" : ""}{factor.weight}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

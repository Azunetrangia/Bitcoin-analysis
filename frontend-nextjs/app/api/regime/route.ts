import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const symbol = searchParams.get("symbol") || "BTCUSDT"
  const algorithm = searchParams.get("algorithm") || "gmm"

  try {
    const regimes = ["bearish", "bearish", "neutral", "bullish", "bullish", "bullish", "bullish"]
    const now = Date.now()

    const data = regimes.map((regime, i) => ({
      timestamp: now - (7 - i) * 86400000,
      regime,
      confidence: 50 + Math.random() * 35,
      probability: {
        bullish: regime === "bullish" ? 60 + Math.random() * 20 : Math.random() * 30,
        bearish: regime === "bearish" ? 60 + Math.random() * 20 : Math.random() * 30,
        neutral: regime === "neutral" ? 60 + Math.random() * 20 : Math.random() * 30,
        high_volatility: Math.random() * 10,
      },
    }))

    return NextResponse.json({
      success: true,
      data,
      symbol,
      algorithm,
    })
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to fetch regime data" }, { status: 500 })
  }
}

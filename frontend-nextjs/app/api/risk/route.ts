import { type NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const symbol = searchParams.get("symbol") || "BTCUSDT"
  const confidence = Number.parseInt(searchParams.get("confidence") || "95")

  try {
    return NextResponse.json({
      success: true,
      data: {
        var_95: -5.24,
        var_99: -6.89,
        var_modified: -6.12,
        sharpe_ratio: 1.24,
        sortino_ratio: 1.68,
        max_drawdown: -12.45,
        current_drawdown: -0.3,
        cvar_95: -6.45,
        skewness: -0.823,
        kurtosis: 2.145,
      },
      symbol,
      confidence,
    })
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to fetch risk metrics" }, { status: 500 })
  }
}

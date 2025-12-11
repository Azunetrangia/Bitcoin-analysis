export interface DashboardStat {
  label: string
  value: string
  description: string
  intent: "positive" | "negative" | "neutral"
  icon: string
  tag?: string
  direction?: "up" | "down"
}

export interface ChartDataPoint {
  date: string
  spendings: number
  sales: number
  coffee: number
}

export interface ChartData {
  week: ChartDataPoint[]
  month: ChartDataPoint[]
  year: ChartDataPoint[]
}

export interface RebelRanking {
  id: number
  name: string
  handle: string
  streak: string
  points: number
  avatar: string
  featured?: boolean
  subtitle?: string
}

export interface SecurityStatus {
  title: string
  value: string
  status: string
  variant: "success" | "warning" | "destructive"
}

export interface Notification {
  id: string
  title: string
  message: string
  timestamp: string
  type: "info" | "warning" | "success" | "error"
  read: boolean
  priority: "low" | "medium" | "high"
}

export interface WidgetData {
  location: string
  timezone: string
  temperature: string
  weather: string
  date: string
}

// Bitcoin-specific types
export interface BitcoinChartConfig {
  showVolume: boolean
  showMovingAverages: boolean
  chartHeight: number
  dateRange: "7D" | "30D" | "90D" | "180D"
}

export interface BitcoinIndicatorSettings {
  rsi: {
    period: number
    overbought: number
    oversold: number
  }
  macd: {
    fast: number
    slow: number
    signal: number
  }
  bollinger: {
    period: number
    stdDev: number
  }
}

export interface BitcoinMetrics {
  currentPrice: number
  priceChange24h: number
  percentChange24h: number
  high24h: number
  low24h: number
  volume24h: number
  marketCap: number
  dominance: number
}

export interface MockData {
  dashboardStats: DashboardStat[]
  chartData: ChartData
  rebelsRanking: RebelRanking[]
  securityStatus: SecurityStatus[]
  notifications: Notification[]
  widgetData: WidgetData
}

export type TimePeriod = "week" | "month" | "year"

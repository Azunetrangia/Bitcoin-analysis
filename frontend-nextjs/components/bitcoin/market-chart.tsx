"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts"

const mockChartData = [
  { date: "Jan 1", price: 42000, volume: 28 },
  { date: "Jan 2", price: 42500, volume: 32 },
  { date: "Jan 3", price: 43000, volume: 35 },
  { date: "Jan 4", price: 44200, volume: 29 },
  { date: "Jan 5", price: 44800, volume: 38 },
  { date: "Jan 6", price: 45230, volume: 42 },
  { date: "Jan 7", price: 45100, volume: 31 },
]

export default function BitcoinChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Price & Volume Analysis</CardTitle>
        <CardDescription>7-day Bitcoin price movement with trading volume</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="price" stroke="#f7931a" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="volume" fill="#4facfe" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

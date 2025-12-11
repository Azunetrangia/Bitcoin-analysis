"use client"

import React from 'react'
import { ResponsiveContainer, ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip, Bar, Cell, ReferenceLine } from 'recharts'

interface CandleData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
  volumeColor?: string
}

interface CandlestickChartProps {
  data: CandleData[]
  showVolume?: boolean
}

// Custom shape component for candlestick
const CandleShape = (props: any) => {
  const { x, y, width, height, payload } = props
  
  if (!payload || !payload.open || !payload.high || !payload.low || !payload.close) {
    return null
  }

  const { open, high, low, close } = payload
  const isGreen = close >= open
  const color = isGreen ? '#22c55e' : '#ef4444'
  
  // Calculate actual pixel positions based on the bar's dimensions
  const ratio = height / (high - low)
  const yHigh = y
  const yLow = y + height
  const yOpen = y + (high - open) * ratio
  const yClose = y + (high - close) * ratio
  
  const centerX = x + width / 2
  const bodyTop = Math.min(yOpen, yClose)
  const bodyHeight = Math.abs(yOpen - yClose) || 1
  const candleWidth = Math.max(width * 0.6, 2)
  
  return (
    <g>
      {/* High-Low Wick */}
      <line
        x1={centerX}
        y1={yHigh}
        x2={centerX}
        y2={yLow}
        stroke={color}
        strokeWidth={1}
      />
      {/* Open-Close Body */}
      <rect
        x={centerX - candleWidth / 2}
        y={bodyTop}
        width={candleWidth}
        height={bodyHeight}
        fill={isGreen ? color : 'transparent'}
        stroke={color}
        strokeWidth={1.5}
      />
    </g>
  )
}

export default function CandlestickChart({ data, showVolume = true }: CandlestickChartProps) {
  // Transform data to have high-low range for Bar chart
  const transformedData = data.map(d => ({
    ...d,
    range: [d.low, d.high]
  }))

  return (
    <div className="space-y-3">
      {/* OHLC Legend */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <span className="text-gray-400 font-semibold">Legend:</span>
          <span className="text-gray-300"><span className="font-semibold text-white">O</span> = Open</span>
          <span className="text-green-400"><span className="font-semibold">H</span> = High</span>
          <span className="text-red-400"><span className="font-semibold">L</span> = Low</span>
          <span className="text-gray-300"><span className="font-semibold text-white">C</span> = Close</span>
          <span className="text-blue-400"><span className="font-semibold">Vol</span> = Volume</span>
          <span className="text-gray-500">|</span>
          <span className="text-green-400">■ Green = Price Up</span>
          <span className="text-red-400">■ Red = Price Down</span>
        </div>
      </div>
      
      <div className="h-96">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={transformedData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            stroke="#9ca3af"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis
            yAxisId="left"
            stroke="#9ca3af"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={['dataMin - 1000', 'dataMax + 1000']}
          />
          {showVolume && (
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
            />
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: '6px',
              color: '#f3f4f6'
            }}
            formatter={(value: any, name: string) => {
              if (name === 'Volume') return [`${Number(value).toFixed(2)} BTC`, name]
              return [`$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, name]
            }}
            content={({ active, payload }) => {
              if (!active || !payload || payload.length === 0) return null
              const data = payload[0].payload
              return (
                <div style={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '6px',
                  padding: '8px',
                  color: '#f3f4f6'
                }}>
                  <p style={{ margin: '2px 0', fontSize: '12px' }}>{data.date}</p>
                  <p style={{ margin: '2px 0', fontSize: '11px' }}>
                    O: ${data.open?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <p style={{ margin: '2px 0', fontSize: '11px', color: '#22c55e' }}>
                    H: ${data.high?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <p style={{ margin: '2px 0', fontSize: '11px', color: '#ef4444' }}>
                    L: ${data.low?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <p style={{ margin: '2px 0', fontSize: '11px' }}>
                    C: ${data.close?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  {showVolume && data.volume && (
                    <p style={{ margin: '2px 0', fontSize: '11px', color: '#4facfe' }}>
                      Vol: {data.volume.toFixed(2)} BTC
                    </p>
                  )}
                </div>
              )
            }}
          />
          
          {/* Candlesticks using Bar with custom shape */}
          <Bar
            yAxisId="left"
            dataKey="range"
            shape={<CandleShape />}
            isAnimationActive={false}
          />
          
          {/* Volume bars */}
          {showVolume && (
            <Bar
              yAxisId="right"
              dataKey="volume"
              isAnimationActive={false}
              radius={[2, 2, 0, 0]}
            >
              {data.map((entry, index) => (
                <Cell key={`vol-${index}`} fill={entry.volumeColor || '#4facfe'} opacity={0.5} />
              ))}
            </Bar>
          )}
        </ComposedChart>
      </ResponsiveContainer>
      </div>
    </div>
  )
}

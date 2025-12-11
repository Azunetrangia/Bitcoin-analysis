// Custom Candlestick shape for Recharts
export const CandlestickShape = (props: any) => {
  const { x, y, width, height, payload } = props
  
  if (!payload || !payload.open || !payload.close || !payload.high || !payload.low) {
    return null
  }

  const isGreen = payload.close >= payload.open
  const color = isGreen ? "#22c55e" : "#ef4444"
  const fillColor = isGreen ? "#22c55e" : "#ef4444"
  
  // Calculate actual pixel positions
  const chartHeight = height
  const priceRange = Math.max(...(payload.high || [0])) - Math.min(...(payload.low || [0]))
  
  if (priceRange === 0) return null
  
  const yScale = (price: number) => {
    const min = Math.min(...(payload.low || [0]))
    const max = Math.max(...(payload.high || [0]))
    return y + (1 - (price - min) / (max - min)) * chartHeight
  }
  
  const openY = yScale(payload.open)
  const closeY = yScale(payload.close)
  const highY = yScale(payload.high)
  const lowY = yScale(payload.low)
  
  const bodyY = Math.min(openY, closeY)
  const bodyHeight = Math.abs(closeY - openY) || 1
  const wickX = x + width / 2
  
  return (
    <g>
      {/* Upper wick */}
      <line
        x1={wickX}
        y1={highY}
        x2={wickX}
        y2={bodyY}
        stroke={color}
        strokeWidth={1}
      />
      
      {/* Body */}
      <rect
        x={x}
        y={bodyY}
        width={width}
        height={bodyHeight}
        fill={fillColor}
        stroke={color}
        strokeWidth={1}
      />
      
      {/* Lower wick */}
      <line
        x1={wickX}
        y1={bodyY + bodyHeight}
        x2={wickX}
        y2={lowY}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  )
}

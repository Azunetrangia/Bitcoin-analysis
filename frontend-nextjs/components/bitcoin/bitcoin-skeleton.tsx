export function BitcoinChartSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-80 bg-muted rounded-lg animate-pulse" />
      <div className="grid grid-cols-4 gap-4">
        {Array(4)
          .fill(0)
          .map((_, i) => (
            <div key={i} className="h-20 bg-muted rounded-lg animate-pulse" />
          ))}
      </div>
    </div>
  )
}

export function MetricsCardSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array(4)
        .fill(0)
        .map((_, i) => (
          <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
        ))}
    </div>
  )
}

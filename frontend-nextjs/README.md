# 🪙 Bitcoin Market Intelligence Dashboard - Next.js Frontend

Modern, beautiful UI for Bitcoin market analysis using Next.js + shadcn/ui + FastAPI backend.

## 🎨 Tech Stack

- **Frontend Framework**: Next.js 14+ (App Router)
- **UI Components**: shadcn/ui + Radix UI
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Backend**: FastAPI (Python) - running separately
- **Data Source**: Real-time from FastAPI `/api/v1` endpoints

## 🚀 Quick Start

### Prerequisites

1. **Node.js** 18+ and pnpm installed
2. **FastAPI backend** running on http://localhost:8000
   - See main project README for backend setup

### Installation

```bash
# Navigate to frontend directory
cd frontend-nextjs

# Install dependencies
pnpm install

# Copy environment file
cp .env.example .env.local

# Start development server
pnpm dev
```

The dashboard will be available at **http://localhost:3000**

## 📁 Project Structure

```
frontend-nextjs/
├── app/                      # Next.js App Router pages
│   ├── page.tsx             # Main dashboard (Overview)
│   ├── bitcoin/
│   │   ├── market/          # Market Overview page ✅
│   │   ├── technical/       # Technical Analysis page (TODO)
│   │   ├── risk/            # Risk Analysis page (TODO)
│   │   └── regime/          # Regime Classification page (TODO)
│   └── layout.tsx           # Root layout with sidebar
│
├── components/
│   ├── dashboard/           # Dashboard layout components
│   │   ├── layout/          # Page layout wrapper
│   │   ├── stat/            # Metric cards
│   │   ├── sidebar/         # Navigation sidebar
│   │   └── ...
│   ├── bitcoin/             # Bitcoin-specific components
│   └── ui/                  # shadcn/ui components
│
├── lib/
│   ├── bitcoin-api.ts       # API client for FastAPI backend ✅
│   ├── bitcoin-types.ts     # TypeScript type definitions
│   └── utils.ts             # Utility functions
│
└── public/                  # Static assets
```

## 🔌 API Integration

### Backend Endpoints Used

The frontend connects to FastAPI backend at `http://localhost:8000/api/v1`:

```typescript
// Market data
GET /market-data/?symbol=BTCUSDT&interval=1h&limit=100

// Technical indicators
GET /analysis/indicators?symbol=BTCUSDT&interval=1h

// Risk metrics
GET /analysis/risk-metrics?symbol=BTCUSDT

// Regime classification
GET /analysis/regimes?symbol=BTCUSDT&interval=1h
```

### Configuration

Edit `.env.local` to change backend URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## 📊 Pages

### ✅ Market Overview (`/bitcoin/market`)

**Features:**
- Real-time price statistics (current, 24h high/low, change)
- Interactive candlestick/line charts
- Moving averages (MA20, MA50, MA200) with signals
- Volume analysis
- Statistical summary (mean, std dev, min, max, median)
- Date range selector (7D, 30D, 90D)

**Data Source:** 
- Market data: `GET /api/v1/market-data/`
- Calculated MAs client-side

### 🚧 Technical Analysis (`/bitcoin/technical`) - TODO

**Planned Features:**
- RSI indicator with overbought/oversold signals
- MACD with histogram
- Bollinger Bands
- Multi-indicator summary with buy/sell signals
- Customizable indicator parameters

**Data Source:** `GET /api/v1/analysis/indicators`

### 🚧 Risk Analysis (`/bitcoin/risk`) - TODO

**Planned Features:**
- Value at Risk (VaR 95%, Modified VaR)
- Sharpe & Sortino Ratios
- Max Drawdown chart
- Volatility Cone
- Risk assessment dashboard

**Data Source:** `GET /api/v1/analysis/risk-metrics`

### 🚧 Regime Classification (`/bitcoin/regime`) - TODO

**Planned Features:**
- Market regime detection (Bullish/Bearish/Neutral/High Volatility)
- Regime timeline chart
- Probability evolution (stacked area)
- Transition matrix heatmap
- Trading implications

**Data Source:** `GET /api/v1/analysis/regimes`

## 🎨 Design System

### Colors

```css
/* Bitcoin Orange */
--bitcoin-orange: #f7931a;

/* Success/Bullish */
--success: #22c55e;

/* Danger/Bearish */
--destructive: #dc3545;

/* Warning */
--warning: #ffc107;

/* Info */
--info: #4facfe;
```

### Components

- **DashboardStat**: Metric card with icon, value, trend indicator
- **DashboardPageLayout**: Consistent page layout with header
- **Card**: shadcn/ui card for sections
- **Charts**: Recharts Line, Bar, Composed charts

## 🛠️ Development

### Available Scripts

```bash
# Development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Lint code
pnpm lint
```

### Adding a New Page

1. Create page file: `app/bitcoin/[page-name]/page.tsx`
2. Use `DashboardPageLayout` wrapper
3. Fetch data using `bitcoinAPI` client
4. Add navigation link in `components/dashboard/sidebar`

Example:

```tsx
"use client"

import { useState, useEffect } from "react"
import DashboardPageLayout from "@/components/dashboard/layout"
import { bitcoinAPI } from "@/lib/bitcoin-api"
import BitcoinIcon from "@/components/icons/bitcoin"

export default function MyPage() {
  const [data, setData] = useState(null)

  useEffect(() => {
    bitcoinAPI.getCandleData("BTCUSDT", "1h").then(setData)
  }, [])

  return (
    <DashboardPageLayout
      header={{
        title: "My Page",
        description: "Page description",
        icon: BitcoinIcon,
      }}
    >
      {/* Your content */}
    </DashboardPageLayout>
  )
}
```

## 🔧 Troubleshooting

### Backend Not Responding

```bash
# Check if FastAPI is running
curl http://localhost:8000/health

# If not, start backend
cd .. # Go to project root
uvicorn src.api.api_server_parquet:app --reload
```

### CORS Errors

Add to FastAPI backend `app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Port Already in Use

```bash
# Change Next.js port
pnpm dev -p 3001
```

## 📝 TODO List

- [x] Setup Next.js project structure
- [x] Configure environment variables
- [x] Create bitcoin-api.ts client
- [x] Build Market Overview page with real data
- [ ] Create Technical Analysis page
- [ ] Create Risk Analysis page  
- [ ] Create Regime Classification page
- [ ] Add error boundaries
- [ ] Add loading states for all pages
- [ ] Add data refresh mechanism
- [ ] Add export/download functionality
- [ ] Mobile responsive optimization
- [ ] Dark/light theme toggle
- [ ] Add unit tests

## 🚀 Deployment

### Production Build

```bash
pnpm build
pnpm start
```

### Environment Variables for Production

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com/api/v1
```

### Docker (Optional)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
```

## 📚 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Recharts Documentation](https://recharts.org/)
- [Tailwind CSS](https://tailwindcss.com/docs)

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test with real FastAPI backend
4. Submit pull request

## 📄 License

MIT License - Same as main project

---

**Built with ❤️ using Next.js + shadcn/ui**  
**Backend**: FastAPI (see main project)  
**Status**: ✅ Market Overview | 🚧 Other pages in progress

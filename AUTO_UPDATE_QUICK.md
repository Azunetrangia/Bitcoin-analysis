# 🔄 Auto Update Quick Guide

## ✅ ĐÃ SETUP XONG - Tự động update khi start!

Bạn **KHÔNG CẦN LÀM GÌ THÊM**. Khi chạy backend, data sẽ tự động update:

```bash
cd /home/azune/Documents/coding/Data-analysis-bitcoin
python -m uvicorn src.api.api_server_parquet:app --reload --host 0.0.0.0 --port 8000
```

### ✅ Kết quả (như logs bạn thấy):

```
INFO: 🚀 Starting Bitcoin Market Intelligence API...
INFO: 🔄 Running auto-update on startup...
INFO: ✅ AUTO UPDATE COMPLETE - 3 intervals updated
INFO: ✅ Server ready!
```

---

## 📊 Hệ thống đã fetch:

- **1h candles**: 9 candles mới (2025-12-11 01:00 → 08:00)
- **4h candles**: 7 candles mới (last 7 periods)
- **1d candles**: 2 candles mới (last 2 days)

---

## 🔄 Muốn manual refresh?

### Option 1: Gọi API

```bash
curl -X POST http://localhost:8000/api/v1/refresh-data
```

### Option 2: Chạy script trực tiếp

```bash
python -m src.services.auto_update_data
```

---

## ⏰ Setup Cron (Optional)

Nếu muốn tự động update mỗi giờ (kể cả khi backend không chạy):

```bash
# Make executable
chmod +x scripts/auto_update.sh

# Add to crontab
crontab -e

# Add line (update every hour):
0 * * * * /home/azune/Documents/coding/Data-analysis-bitcoin/scripts/auto_update.sh
```

---

## 📁 Files Created/Modified:

1. ✅ **src/services/auto_update_data.py** - Core auto-update logic
2. ✅ **src/api/api_server_parquet.py** - Added startup event + refresh endpoint
3. ✅ **scripts/auto_update.sh** - Updated to use new script

---

## 🎯 Cách hoạt động:

```
1. Backend starts
   ↓
2. Check last timestamp in parquet file (e.g., 2025-12-11 01:00)
   ↓
3. Fetch new data from Binance (01:00 → now)
   ↓
4. Merge with existing data (remove duplicates)
   ↓
5. Save updated parquet file
   ↓
6. Clear cache → Ready!
```

---

## ✨ Smart Features:

- ✅ **Incremental**: Chỉ fetch data MỚI (không re-download tất cả)
- ✅ **Fast**: ~2-5 seconds cho 3 intervals
- ✅ **Safe**: Xử lý duplicates tự động
- ✅ **Graceful**: Nếu lỗi, dùng data cũ (không crash)
- ✅ **Multi-interval**: Update 1h, 4h, 1d cùng lúc

---

## 📋 Manual Commands:

```bash
# Check current data
python -c "
import pandas as pd
df = pd.read_parquet('data/hot/BTCUSDT_1h.parquet')
print(f'Last: {df[\"time\"].max()}')
print(f'Total: {len(df)} candles')
"

# Force update now
python -m src.services.auto_update_data

# Call API refresh
curl -X POST http://localhost:8000/api/v1/refresh-data
```

---

**Status:** ✅ WORKING (tested on 2025-12-11 08:00)

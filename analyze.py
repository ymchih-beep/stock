import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import datetime
import time

# 設定股票清單
stock_list = ['2330.TW', '2317.TW', '2454.TW', '0050.TW', '2603.TW', '3653.TW']
results = {}

def check_pattern(df):
    patterns = []
    
    if len(df) < 20: return ["資料不足"] # 資料太少不分析
    
    # 1. 計算均線
    df['SMA_5'] = ta.sma(df['Close'], length=5)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    
    # 取得最新一筆資料
    current_sma5 = df['SMA_5'].iloc[-1]
    current_sma20 = df['SMA_20'].iloc[-1]
    close_price = df['Close'].iloc[-1]
    
    # --- 判斷 1: 均線 ---
    if current_sma5 > current_sma20:
        patterns.append("均線多頭 (5>20)")
    else:
        patterns.append("均線空頭 (5<20)")
        
    # --- 判斷 2: KD 指標 ---
    # 使用 pandas_ta 計算 KD
    stoch = df.ta.stoch(k=9, d=3, append=True)
    # 欄位名稱動態抓取 (避免名稱不同)
    k_col = [c for c in df.columns if c.startswith('STOCHk')][0]
    d_col = [c for c in df.columns if c.startswith('STOCHd')][0]
    
    k_val = df[k_col].iloc[-1]
    d_val = df[d_col].iloc[-1]
    prev_k = df[k_col].iloc[-2]
    prev_d = df[d_col].iloc[-2]

    if prev_k < prev_d and k_val > d_val:
        patterns.append("KD黃金交叉 ↗")
    elif prev_k > prev_d and k_val < d_val:
        patterns.append("KD死亡交叉 ↘")

    return patterns

print("=== 開始分析股票 (防擋機制啟動) ===")

for symbol in stock_list:
    try:
        print(f"正在下載: {symbol} ...")
        
        # 使用 Ticker 物件抓取，通常比直接 download 穩定
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")
        
        if df.empty:
            print(f"⚠️ {symbol} 下載失敗 (資料為空)")
            continue

        # 簡單資料處理
        patterns = check_pattern(df)
        clean_code = symbol.replace('.TW', '').replace('.TWO', '')
        last_price = round(float(df['Close'].iloc[-1]), 2)
        
        results[clean_code] = {
            "price": last_price,
            "patterns": patterns,
            "date": str(datetime.date.today())
        }
        print(f"✅ {clean_code} 分析成功: {last_price} {patterns}")
        
        # 暫停 2 秒，避免請求太快被 Yahoo 封鎖
        time.sleep(2)

    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")

# 確保就算沒資料也要存一個空檔或舊檔，避免網頁壞掉
print(f"總共完成 {len(results)} 檔股票分析")

with open('stock_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print("資料儲存完成。")

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import datetime

# 範例：我們要分析的股票清單 (你可以擴充成台灣50或是全部上市櫃)
# 格式：股票代號.TW (上市) 或 .TWO (上櫃)
stock_list = ['2330.TW', '2317.TW', '2454.TW', '0050.TW', '2603.TW'] 

results = {}

def check_pattern(df):
    """
    這裡定義你的技術分析邏輯
    回傳：符合的型態名稱清單
    """
    patterns = []
    
    # 1. 取得最近兩筆資料
    if len(df) < 5: return ["資料不足"]
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    
    # --- 範例指標 1: 均線多頭排列 (SMA 5 > SMA 20) ---
    # 使用 pandas_ta 計算
    df['SMA_5'] = ta.sma(df['Close'], length=5)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    
    current_sma5 = df['SMA_5'].iloc[-1]
    current_sma20 = df['SMA_20'].iloc[-1]
    
    if current_sma5 > current_sma20:
        patterns.append("均線多頭 (5日 > 20日)")
        
    # --- 範例指標 2: KD 黃金交叉 ---
    # K < 20 且 K 向上突破 D
    k_period = 9
    d_period = 3
    df.ta.stoch(k=k_period, d=d_period, append=True)
    # 欄位名稱通常是 STOCHk_9_3_3 和 STOCHd_9_3_3
    k_col = f'STOCHk_{k_period}_{d_period}_3'
    d_col = f'STOCHd_{k_period}_{d_period}_3'
    
    if (df[k_col].iloc[-2] < df[d_col].iloc[-2]) and \
       (df[k_col].iloc[-1] > df[d_col].iloc[-1]) and \
       (df[k_col].iloc[-1] < 80): # 這裡簡單示範
        patterns.append("KD黃金交叉")

    # --- 範例指標 3: 紅三兵 (連續三天收紅) ---
    if (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and \
       (df['Close'].iloc[-2] > df['Open'].iloc[-2]) and \
       (df['Close'].iloc[-3] > df['Open'].iloc[-3]):
        patterns.append("紅三兵 K線型態")

    if not patterns:
        patterns.append("盤整/無特殊型態")
        
    return patterns

print("開始分析股票...")

for symbol in stock_list:
    try:
        # 下載資料 (日K)
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        
        if not df.empty:
            patterns = check_pattern(df)
            # 移除 .TW 以便搜尋
            clean_code = symbol.replace('.TW', '').replace('.TWO', '')
            
            # 取得最後收盤價
            last_price = round(float(df['Close'].iloc[-1]), 2)
            
            results[clean_code] = {
                "price": last_price,
                "patterns": patterns,
                "date": str(datetime.date.today())
            }
            print(f"{clean_code} 分析完成: {patterns}")
            
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")

# 儲存結果到 JSON 檔案
with open('stock_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print("資料儲存完成。")
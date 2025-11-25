import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import datetime
import time
import requests
from io import StringIO

# --- 設定 ---
stock_list = ['2330.TW', '2317.TW', '2454.TW', '0050.TW', '2603.TW', '3653.TW']
results = {}

# 取得股票名稱的快取 (避免重複查詢 TWSE)
STOCK_NAMES = {}

def get_stock_name(stock_code):
    """從公開資訊觀測站抓取股票名稱 (此處使用簡易爬蟲)"""
    if stock_code in STOCK_NAMES:
        return STOCK_NAMES[stock_code]
    
    # 這裡抓 TWSE 的 JSON 檔案
    # 注意：這個 URL 的結構可能會變動
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.date.today().strftime('%Y%m%d')}&stockNo={stock_code}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'title' in data:
            # title 格式通常是 "110年11月 2330 台積電"
            name = data['title'].split(' ')[-1]
            STOCK_NAMES[stock_code] = name
            return name
    except Exception as e:
        # print(f"無法取得名稱: {e}")
        pass
        
    return "N/A" # 如果抓不到，回傳 N/A

def check_pattern(df):
    patterns = []
    
    if len(df) < 20: return {"patterns": ["資料不足"], "ma_status": "N/A"}
    
    # ... (K線型態判斷，維持原本的邏輯，這裡省略以保持簡潔) ...
    # 1. 均線
    df['SMA_5'] = ta.sma(df['Close'], length=5)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    
    current_sma5 = df['SMA_5'].iloc[-1]
    current_sma20 = df['SMA_20'].iloc[-1]
    
    ma_status = "均線空頭 (5<20)"
    if current_sma5 > current_sma20:
        patterns.append("均線多頭 (5>20)")
        ma_status = "均線多頭 (5>20)"
    else:
        patterns.append("均線空頭 (5<20)")
        
    # 2. KD 指標
    stoch = df.ta.stoch(k=9, d=3, append=True)
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
        
    return {"patterns": patterns, "ma_status": ma_status}

def get_major_investor_data(target_date):
    """
    從 TWSE 抓取三大法人買賣超
    """
    today_str = target_date.strftime('%Y%m%d')
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={today_str}&selectType=ALL"
    
    try:
        # TWSE 需要 header 才能順利抓取
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers)
        data = res.json()
        
        investor_data = {}
        if 'data' in data:
            # 格式: [股票代號, 股票名稱, 外資買進, 外資賣出, 外資淨額, ... ]
            for row in data['data']:
                try:
                    code = row[0].strip()
                    # 淨額在欄位 [10]
                    net_buy_sell = int(row[10].replace(',', ''))
                    # 單位是張 (1000 股)，換算成百萬
                    net_buy_sell_million = round(net_buy_sell * 1000 / 1000000, 2)
                    investor_data[code] = f"{net_buy_sell_million:.2f} 百萬"
                except:
                    continue
        return investor_data
        
    except Exception as e:
        print(f"三大法人資料抓取失敗: {e}")
        return {}

# --- 主要執行區塊 ---
print("=== 開始分析股票與抓取輔助數據 ===")

# 1. 抓取三大法人資料
investor_data = get_major_investor_data(datetime.date.today())
print(f"三大法人資料已取得 {len(investor_data)} 筆。")


for symbol_dot_tw in stock_list:
    clean_code = symbol_dot_tw.replace('.TW', '').replace('.TWO', '')
    
    try:
        # 抓取名稱
        name = get_stock_name(clean_code)
        
        # 2. 抓取股價資料
        ticker = yf.Ticker(symbol_dot_tw)
        df = ticker.history(period="6mo")
        
        if df.empty:
            print(f"⚠️ {clean_code} 下載失敗 (資料為空)")
            continue

        # 3. 執行分析
        analysis_result = check_pattern(df)
        last_price = round(float(df['Close'].iloc[-1]), 2)
        
        # 4. 取得三大法人淨額
        investor_net = investor_data.get(clean_code, "N/A")

        results[clean_code] = {
            "name": name,
            "price": last_price,
            "patterns": analysis_result["patterns"],
            "ma_status": analysis_result["ma_status"],
            "investor_net": investor_net,
            "date": str(datetime.date.today())
        }
        print(f"✅ {clean_code} ({name}) 分析成功: {last_price}, 法人:{investor_net}")
        
        time.sleep(1) # 暫停 1 秒

    except Exception as e:
        print(f"❌ Error analyzing {symbol_dot_tw}: {e}")

# 儲存結果到 JSON 檔案
with open('stock_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print("資料儲存完成。")

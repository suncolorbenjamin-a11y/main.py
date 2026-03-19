import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# 1. 雲端授權設定 (這部分不要動)
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_client():
    # 這裡會讀取你的 google_key.json
    creds = Credentials.from_service_account_file("google_key.json", scopes=SCOPE)
    return gspread.authorize(creds)

# --- 以下函式名稱與參數完全對齊你的舊代碼 ---

def load_data():
    """從 Google Sheets 載入資料，並回傳與 JSON 格式一模一樣的字典"""
    try:
        client = get_client()
        sh = client.open("study-tracking-center")
        
        # 讀取試算表中的分頁
        sub_df = pd.DataFrame(sh.worksheet("subjects_data").get_all_records())
        hist_df = pd.DataFrame(sh.worksheet("history_data").get_all_records())
        
        # 建立結構 (對齊你 JSON 的結構)
        db = {"subjects": {}, "history": hist_df.to_dict('records')}
        
        for _, row in sub_df.iterrows():
            sub_name = row['subject']
            if sub_name not in db["subjects"]:
                db["subjects"][sub_name] = {
                    "class_time": row['class_time'], 
                    "last_reset": row['last_reset'], 
                    "tasks": {}
                }
            # 回填任務
            db["subjects"][sub_name]["tasks"][row['task']] = {
                "done": float(row['done']), 
                "total": float(row['total']), 
                "type": row['type']
            }
        return db
    except Exception as e:
        # 如果雲端失敗，至少回傳一個空的結構讓 app.py 不會壞掉
        print(f"雲端連線異常: {e}")
        return {"subjects": {}, "history": []}

def save_data(data): # 👈 參數名稱對齊你的 "data"
    """將資料同步回雲端試算表"""
    try:
        client = get_client()
        sh = client.open("study-tracking-center")
        
        # 1. 處理科目分頁
        sub_rows = []
        for sub, info in data["subjects"].items():
            for task, t_info in info["tasks"].items():
                sub_rows.append({
                    "subject": sub, 
                    "class_time": info.get("class_time", ""), 
                    "last_reset": info.get("last_reset", ""),
                    "task": task, 
                    "done": t_info["done"], 
                    "total": t_info["total"], 
                    "type": t_info.get("type", "知識內化")
                })
        
        if sub_rows:
            ws_sub = sh.worksheet("subjects_data")
            ws_sub.clear()
            ws_sub.update([list(sub_rows[0].keys())] + [list(r.values()) for r in sub_rows])

        # 2. 處理歷史分頁
        if data["history"]:
            ws_hist = sh.worksheet("history_data")
            ws_hist.clear()
            ws_hist.update([list(data["history"][0].keys())] + [list(r.values()) for r in data["history"]])
    except Exception as e:
        print(f"雲端儲存失敗: {e}")

def log_activity(data, subject, solved_increment): # 👈 參數完全對齊你的舊代碼
    """即時紀錄產出到雲端 history 分頁"""
    today = str(datetime.now().date())
    
    # 跟你的舊邏輯一樣：今天有紀錄就累加，沒有就新增
    found = False
    for entry in data["history"]:
        if entry["date"] == today and entry["subject"] == subject:
            entry["solved"] += solved_increment
            found = True
            break
    
    if not found:
        data["history"].append({
            "date": today,
            "subject": subject,
            "solved": solved_increment,
            "total": 0,
            "type": "未分類"
        })
    
    # 💡 關鍵：紀錄完後立刻執行雲端存檔
    save_data(data)
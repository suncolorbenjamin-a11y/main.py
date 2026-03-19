import pandas as pd
from datetime import datetime

def calculate_subject_progress(tasks):
    """計算單科總進度 (防撞版：同時支援新舊格式)"""
    if not tasks: return 0
    total_w = 0
    earned_w = 0
    
    for t in tasks.values():
        # 判斷是新格式(字典)還是舊格式(清單)
        if isinstance(t, dict):
            done, total, weight = t.get("done", 0), t.get("total", 0), t.get("weight", 1)
        elif isinstance(t, list) and len(t) >= 3:
            done, total, weight = t[0], t[1], t[2]
        else: continue
            
        if total > 0:
            total_w += weight
            earned_w += (done / total) * weight
            
    return (earned_w / total_w * 100) if total_w > 0 else 0

def get_total_stats_by_type(subjects):
    """分類統計：實戰看題數，內化看小時 (防撞版)"""
    stats = {"實戰演練": 0, "知識內化": 0.0}
    for sub in subjects.values():
        for t in sub.get("tasks", {}).values():
            # 關鍵防護區
            if isinstance(t, dict):
                t_type = t.get("type", "知識內化")
                val = t.get("done", 0)
            else: # 處理舊的 [done, total, weight] 清單格式
                t_type = "知識內化" # 舊格式統一歸類到內化
                val = t[0] if len(t) > 0 else 0
            
            if "實戰" in t_type:
                stats["實戰演練"] += int(val)
            else:
                stats["知識內化"] += float(val)
    return stats

from datetime import datetime, timedelta

def get_urgency_report(subjects):
    """精準小時制急迫性評分"""
    now = datetime.now()
    today_idx = now.weekday()
    report = []
    
    for name, info in subjects.items():
        # 1. 取得設定的上課時間 (預設 09:00)
        time_str = info.get("class_time", "09:00")
        t_hour, t_min = map(int, time_str.split(":"))
        
        # 2. 找出下一個最近的上課日期
        # 先檢查今天是否還有課（且還沒過時間）
        next_class_dt = None
        days_to_check = sorted(info["schedule"])
        
        # 找尋本週或下週最靠近的時間點
        found = False
        for day_offset in range(8): # 檢查今天到下週同一天
            check_day = (today_idx + day_offset) % 7
            if check_day in info["schedule"]:
                potential_dt = now.replace(hour=t_hour, minute=t_min, second=0, microsecond=0) + timedelta(days=day_offset)
                if potential_dt > now:
                    next_class_dt = potential_dt
                    found = True
                    break
        
        if not next_class_dt: continue

        # 3. 計算精確剩餘小時 (含小數點)
        time_diff = next_class_dt - now
        hours_left = time_diff.total_seconds() / 3600
        
        progress = calculate_subject_progress(info.get("tasks", {}))
        
        # --- (這裡是你計算 h_left 和 prog 的地方) ---

        # 1. 先把圖二的判斷邏輯放進來 (決定 status 和 priority)
        if progress >= 100:
            status = "✅" 
            status_priority = 0 
        elif hours_left <= 24 and progress < 80:
            status = "🔴" 
            status_priority = 3 
        elif hours_left <= 24 or progress < 50:
            status = "🟡" 
            status_priority = 2
        else:
            status = "🟢" 
            status_priority = 1

        # 2. 計算分數 (根據我們剛才討論的三層邏輯)
        score = (status_priority * 10000) + (1000 / (hours_left + 0.1)) + (100 - progress)

        # 3. 最後把結果打包塞進 report 裡
        report.append({
            "name": name,
            "hours_left": round(hours_left, 1),
            "progress": progress,
            "score": score,   # 這裡用計算後的 score
            "status": status  # 這裡用判斷後的符號
        })

    # 迴圈結束後進行排序
    return sorted(report, key=lambda x: x["score"], reverse=True)
    

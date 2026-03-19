import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def show_analytics_dashboard(history):
    if not history:
        st.info("💡 目前尚無歷史數據。點擊幾次任務的『➕』，這裡就會立刻出現能量圖！")
        return

    # 1. 數據標準化
    df = pd.DataFrame(history)
    df['date'] = pd.to_datetime(df['date'])
    
    st.header("📈 考研戰略分析中心")
    st.write("---")

    # --- A. 七日滾動產出 (能量趨勢) ---
    st.subheader("⚔️ 七日滾動產出 (Rolling Output)")
    st.caption("顯示過去 7 天的每日即時產出累積，反映你的讀書節奏。")

    if 'subject' in df.columns:
        # 建立連續日期，確保沒讀書的日子也會顯示 0
        all_dates = pd.date_range(start=df['date'].min(), end=df['date'].max()).date
        all_subjects = df['subject'].unique()
        idx = pd.MultiIndex.from_product([all_dates, all_subjects], names=['date', 'subject'])
        
        # 重新整理數據
        daily_data = df.groupby(['date', 'subject'])['solved'].sum().reset_index()
        daily_data['date'] = daily_data['date'].dt.date
        full_df = pd.DataFrame(index=idx).reset_index()
        full_df = pd.merge(full_df, daily_data, on=['date', 'subject'], how='left').fillna(0)
        
        # 計算 7 日滾動總和
        full_df = full_df.sort_values(['subject', 'date'])
        full_df['rolling_7d'] = full_df.groupby('subject')['solved'].transform(
            lambda x: x.rolling(window=7, min_periods=1).sum()
        )
        
        fig_rolling = px.area(full_df, x='date', y='rolling_7d', color='subject',
                            line_shape='spline', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_rolling.update_layout(hovermode="x unified")
        st.plotly_chart(fig_rolling, use_container_width=True)

    # --- B. 週期性狀態評估 (Achievement Rate) ---
    st.write("---")
    st.subheader("🚩 週期性狀態評估")
    
    if 'total' in df.columns and df['total'].sum() > 0:
        # 按週分組 (ISO週)
        df['week'] = df['date'].dt.strftime('%Y-W%V')
        weekly_stats = df.groupby('week').agg({'solved': 'sum', 'total': 'sum'}).reset_index()
        
        # 關鍵：達成率公式
        weekly_stats['rate'] = (weekly_stats['solved'] / weekly_stats['total'] * 100).round(1)
        
        # 根據達成率定義顏色
        def get_color(rate):
            if rate >= 80: return '#00CC96' # 綠色
            if rate >= 60: return '#FFA421' # 黃色
            return '#FF4B4B'                # 紅色

        weekly_stats['color'] = weekly_stats['rate'].apply(get_color)

        fig_rate = px.bar(weekly_stats, x='week', y='rate', text='rate',
                          labels={'rate': '達成率 (%)', 'week': '年度週次'})
        
        fig_rate.update_traces(marker_color=weekly_stats['color'], textposition='outside')
        fig_rate.add_hline(y=80, line_dash="dash", line_color="white", annotation_text="及格門檻 (80%)")
        
        st.plotly_chart(fig_rate, use_container_width=True)
        
        # 顯示狀態提示
        latest_rate = weekly_stats.iloc[-1]['rate']
        if latest_rate < 60:
            st.error(f"⚠️ 狀態低迷：本週目前達成率僅 {latest_rate}% - 需檢討政大雜事過多或目標掛太高。")
        elif latest_rate < 80:
            st.warning(f"📒 狀態一般：本週達成率 {latest_rate}% - 還有衝刺空間！")
        else:
            st.success(f"🔥 狀態極佳：本週達成率 {latest_rate}% - 保持這個節奏衝向台大！")
    else:
        st.info("💡 達成率需要有『本週目標量』才能計算。請等待下一次科目自動結算。")

    # --- 下方的圓餅圖與雷達圖保持不變 ---
    col_pie, col_radar = st.columns(2)
    with col_pie:
        st.subheader("🍰 科目總產出佔比")
        sub_dist = df.groupby('subject')['solved'].sum().reset_index()
        st.plotly_chart(px.pie(sub_dist, values='solved', names='subject', hole=0.4), use_container_width=True)

    with col_radar:
        st.subheader("🕸️ 戰力平衡雷達")
        sub_avg = df.groupby('subject')['solved'].mean().reset_index()
        fig_radar = go.Figure(data=go.Scatterpolar(r=sub_avg['solved'], theta=sub_avg['subject'], fill='toself'))
        st.plotly_chart(fig_radar, use_container_width=True)
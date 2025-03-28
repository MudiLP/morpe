import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Настройка страницы
st.set_page_config(page_title="Price History Viewer", layout="wide")

# Функция загрузки данных изображений
@st.cache_data
def load_image_data():
    try:
        with open("data/img.csv", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        img_dict = {}
        for line in lines[1:]:  # пропускаем заголовок
            split_index = line.find("https://")
            if split_index != -1:
                name = line[:split_index].strip()
                img = line[split_index:].strip()
                img_dict[name] = img
                
        return img_dict
        
    except FileNotFoundError:
        st.error("Файл img.csv не найден.")
        return {}
    except Exception as e:
        st.error(f"Ошибка при чтении файла img.csv: {str(e)}")
        return {}

@st.cache_data(ttl=60)
def load_data():
    file_path = "data/price_history.csv"
    last_modified = os.path.getmtime(file_path)
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df, last_modified

@st.cache_data
def load_supply_data():
    supply_path = "data/nft_supply_results.csv"
    try:
        supply_df = pd.read_csv(supply_path)
        supply_dict = dict(zip(supply_df['Item Name'], supply_df['Estimated Supply']))
        return supply_dict
    except FileNotFoundError:
        st.error(f"Файл {supply_path} не найден.")
        return {}

def get_time_filtered_data(df, minutes):
    if minutes == 0:  # Показать все данные
        return df
    
    now = df['timestamp'].max()
    start_time = now - timedelta(minutes=minutes)
    return df[df['timestamp'] >= start_time]

def format_time_label(minutes):
    if minutes == 0:
        return "All"
    elif minutes < 60:
        return f"{minutes}min"
    elif minutes < 1440:  # меньше 24 часов
        hours = minutes // 60
        return f"{hours}h"
    else:
        days = minutes // 1440
        return f"{days}d"

def main():
    # Загрузка всех данных
    df, _ = load_data()
    supply_dict = load_supply_data()
    img_dict = load_image_data()
    default_img = "https://i.ibb.co/tpZ9HsSY/photo-2023-12-23-09-42-33.jpg"

    st.title("Price History Analysis")
    
    items = [col for col in df.columns if col != 'timestamp']
    items_with_supply = [f"{item} (Supply: {int(supply_dict.get(item, 0))})" for item in items]
    display_to_original = dict(zip(items_with_supply, items))
    
    # Боковая панель с фильтрами
    with st.sidebar:
        st.header("Фильтры")
        
        selected_items_with_supply = st.multiselect(
            f"Выберите предметы (всего: {len(items)})",
            items_with_supply,
            default=[items_with_supply[0]] if items_with_supply else []
        )
        
        selected_items = [display_to_original[item] for item in selected_items_with_supply]
        
        # Временные интервалы в минутах
        time_intervals = {
            0: "All",        # 0 минут = все данные
            30: "30min",     # 30 минут
            60: "1h",        # 1 час
            720: "12h",      # 12 часов
            1440: "1d",      # 1 день
            10080: "7d",     # 7 дней
        }
        
        selected_minutes = st.select_slider(
            "Временной интервал",
            options=list(time_intervals.keys()),
            value=0,
            format_func=format_time_label
        )
        
        show_ma = st.checkbox("Показать скользящую среднюю", value=True)
        if show_ma:
            ma_period = st.slider("Период скользящей средней (часов)", 1, 24, 6)

    if selected_items:
        # Фильтруем данные по выбранному временному интервалу
        filtered_df = get_time_filtered_data(df, selected_minutes)
        
        fig = go.Figure()
        
        for item in selected_items:
            fig.add_trace(go.Scatter(
                x=filtered_df['timestamp'],
                y=filtered_df[item],
                mode='lines',
                name=f"{item} (Supply: {int(supply_dict.get(item, 0))})"
            ))
            
            if show_ma:
                window = int(ma_period * 2)
                ma = filtered_df[item].rolling(window=window).mean()
                fig.add_trace(go.Scatter(
                    x=filtered_df['timestamp'],
                    y=ma,
                    mode='lines',
                    line=dict(dash='dash'),
                    name=f'{item} MA({ma_period}h)'
                ))
        
        fig.update_layout(
            height=600,
            xaxis_title="Время",
            yaxis_title="Цена",
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
                
if __name__ == "__main__":
    main()

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
        
        # Создаем максимально детальные временные интервалы
        time_intervals = [
            0,      # All
            1,      # 1 минута
            2,      # 2 минуты
            3,      # 3 минуты
            5,      # 5 минут
            7,      # 7 минут
            10,     # 10 минут
            15,     # 15 минут
            20,     # 20 минут
            25,     # 25 минут
            30,     # 30 минут
            35,     # 35 минут
            40,     # 40 минут
            45,     # 45 минут
            50,     # 50 минут
            55,     # 55 минут
            60,     # 1 час
            90,     # 1.5 часа
            120,    # 2 часа
            150,    # 2.5 часа
            180,    # 3 часа
            210,    # 3.5 часа
            240,    # 4 часа
            300,    # 5 часов
            360,    # 6 часов
            420,    # 7 часов
            480,    # 8 часов
            540,    # 9 часов
            600,    # 10 часов
            660,    # 11 часов
            720,    # 12 часов
            840,    # 14 часов
            960,    # 16 часов
            1080,   # 18 часов
            1200,   # 20 часов
            1320,   # 22 часа
            1440,   # 1 день
            1800,   # 1.25 дня
            2160,   # 1.5 дня
            2880,   # 2 дня
            3600,   # 2.5 дня
            4320,   # 3 дня
            5040,   # 3.5 дня
            5760,   # 4 дня
            6480,   # 4.5 дня
            7200,   # 5 дней
            7920,   # 5.5 дней
            8640,   # 6 дней
            9360,   # 6.5 дней
            10080   # 7 дней
        ]

        def format_time_label(minutes):
            if minutes == 0:
                return "All"
            elif minutes < 60:
                return f"{minutes}min"
            elif minutes < 1440:
                hours = minutes / 60
                if hours.is_integer():
                    return f"{int(hours)}h"
                return f"{hours:.1f}h"
            else:
                days = minutes / 1440
                if days.is_integer():
                    return f"{int(days)}d"
                return f"{days:.1f}d"

        # Добавляем две опции отображения временного интервала
        time_selector_type = st.radio(
            "Тип выбора времени",
            ["Бегунок", "Точный ввод"],
            horizontal=True
        )

        if time_selector_type == "Бегунок":
            selected_minutes = st.select_slider(
                "Временной интервал",
                options=time_intervals,
                value=0,
                format_func=format_time_label
            )
        else:
            selected_minutes = st.slider(
                "Временной интервал (минуты)",
                min_value=0,
                max_value=10080,
                value=0,
                step=1
            )

        # Показываем точное значение выбранного интервала
        if selected_minutes > 0:
            hours = selected_minutes / 60
            days = selected_minutes / 1440
            st.caption(
                f"Выбранный интервал: \n"
                f"- {selected_minutes} минут\n"
                f"- {hours:.2f} часов\n"
                f"- {days:.2f} дней"
            )
        
        st.plotly_chart(fig, use_container_width=True)
                
if __name__ == "__main__":
    main()

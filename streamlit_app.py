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

def main():
    # Загрузка всех данных
    df, _ = load_data()
    supply_dict = load_supply_data()
    img_dict = load_image_data()
    default_img = "https://i.ibb.co/tpZ9HsSY/photo-2023-12-23-09-42-33.jpg"

    # Заголовок и процентное изменение в одной строке
    col1, col2 = st.columns([2, 1])
    with col1:
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
        
        date_range = st.date_input(
            "Выберите период",
            value=(df['timestamp'].min().date(), df['timestamp'].max().date()),
            min_value=df['timestamp'].min().date(),
            max_value=df['timestamp'].max().date()
        )
        
        show_ma = st.checkbox("Показать скользящую среднюю", value=True)
        if show_ma:
            ma_period = st.slider("Период скользящей средней (часов)", 1, 24, 6)

    # После определения selected_items и date_range добавляем процентное изменение
    with col2:
        if selected_items and len(selected_items) == 1:
            item = selected_items[0]
            mask = (df['timestamp'].dt.date >= date_range[0]) & (df['timestamp'].dt.date <= date_range[1])
            filtered_df = df.loc[mask]
            
            start_price = filtered_df[item].iloc[0]
            end_price = filtered_df[item].iloc[-1]
            price_change = end_price - start_price
            price_change_percent = (price_change / start_price) * 100
            
            price_change_color = "green" if price_change >= 0 else "red"
            price_change_arrow = "↑" if price_change >= 0 else "↓"
            
            st.markdown(
                f"<h2 style='color: {price_change_color}; text-align: right; margin-top: 15px;'>{price_change_arrow} {abs(price_change_percent):.2f}%</h2>",
                unsafe_allow_html=True
            )

    # Проверка date_range
    if len(date_range) != 2:
        st.error("Пожалуйста, выберите две даты для определения периода")
        return

        # Отображение графика и статистики
    if selected_items:
        # График (оставляем только одну обработку filtered_df)
        mask = (df['timestamp'].dt.date >= date_range[0]) & (df['timestamp'].dt.date <= date_range[1])
        filtered_df = df.loc[mask]
        
        # Добавляем создание объекта Figure
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
        
        if len(selected_items) == 1:
            item = selected_items[0]
            
            # Расчет процентного изменения
            start_price = filtered_df[item].iloc[0]  # Цена в начале периода
            end_price = filtered_df[item].iloc[-1]   # Цена в конце периода
            price_change = end_price - start_price
            price_change_percent = (price_change / start_price) * 100

            img_col, stats_col = st.columns([1, 2])
            
            with img_col:
                img_url = img_dict.get(item, default_img)
                st.image(img_url, use_container_width=True)
            
            with stats_col:
                st.subheader(f"Статистика - {item}")
                col1, col2, col3, col4, col5 = st.columns(5)  # Добавили пятую колонку
                
                current_price = filtered_df[item].iloc[-1]
                min_price = filtered_df[item].min()
                max_price = filtered_df[item].max()
                supply = supply_dict.get(item, 0)
                volatility = ((max_price - min_price) / min_price) * 100
                
                # Сначала отображаем метрики
                col1.metric("Текущая цена", f"{current_price:.2f}")
                col2.metric("Минимальная цена", f"{min_price:.2f}")
                col3.metric("Максимальная цена", f"{max_price:.2f}")
                col4.metric("Supply", f"{int(supply)}")
                col5.metric("Волатильность", f"{volatility:.2f}%")

                # Затем добавляем разделитель и анализ волатильности
                st.markdown("---")  # разделитель
                st.subheader("Анализ волатильности")
                
                def calculate_volatility(df, item):
                    if len(df) < 2:
                        return None
                    min_price = df[item].min()
                    max_price = df[item].max()
                    return ((max_price - min_price) / min_price) * 100

                # Получаем текущую дату из данных
                current_date = df['timestamp'].max()

                # Расчет волатильности за разные периоды
                vol_cols = st.columns(4)
                
                # За день
                day_mask = df['timestamp'] >= (current_date - pd.Timedelta(days=1))
                day_df = df.loc[day_mask]
                day_vol = calculate_volatility(day_df, item)
                
                # За неделю
                week_mask = df['timestamp'] >= (current_date - pd.Timedelta(days=7))
                week_df = df.loc[week_mask]
                week_vol = calculate_volatility(week_df, item)
                
                # За месяц
                month_mask = df['timestamp'] >= (current_date - pd.Timedelta(days=30))
                month_df = df.loc[month_mask]
                month_vol = calculate_volatility(month_df, item)
                
                # За всё время
                total_vol = volatility  # используем уже рассчитанную общую волатильность

                def get_volatility_status(vol):
                    if vol is None:
                        return "Нет данных", "gray"
                    elif vol < 10:
                        return "Низкая", "green"
                    elif vol < 30:
                        return "Средняя", "orange"
                    else:
                        return "Высокая", "red"

                # Отображение результатов с цветовой индикацией
                periods = [
                    ("24 часа", day_vol),
                    ("7 дней", week_vol),
                    ("30 дней", month_vol),
                    ("Общая", total_vol)
                ]

                for i, (period, vol) in enumerate(periods):
                    status, color = get_volatility_status(vol)
                    with vol_cols[i]:
                        if vol is not None:
                            st.markdown(
                                f"""
                                <div style='text-align: center'>
                                    <p style='font-weight: bold'>{period}</p>
                                    <p style='color: {color}; font-size: 24px'>{vol:.2f}%</p>
                                    <p style='color: {color}'>{status}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f"""
                                <div style='text-align: center'>
                                    <p style='font-weight: bold'>{period}</p>
                                    <p style='color: gray'>Нет данных</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                # Добавляем пояснение
                st.markdown("""
                **Интерпретация волатильности:**
                - 🟢 **Низкая** (<10%): Стабильный рынок, низкий риск, подходит для долгосрочных инвестиций
                - 🟡 **Средняя** (10-30%): Умеренные колебания, сбалансированный риск, подходит для среднесрочной торговли
                - 🔴 **Высокая** (>30%): Сильные колебания, высокий риск/потенциал, подходит для краткосрочной торговли
                """)
                
if __name__ == "__main__":
    main()

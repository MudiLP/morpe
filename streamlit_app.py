import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Page configuration
st.set_page_config(page_title="Price History Viewer", layout="wide")

# Image data loading function
@st.cache_data
def load_image_data():
    file_path = "data/img.csv"
    
    try:
        # Читаем файл вручную
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        img_dict = {}
        # Пропускаем заголовок
        for line in lines[1:]:
            # Разделяем строку по запятой, но только на первое вхождение
            parts = line.split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip().strip('"')
                url = parts[1].strip().strip('"')
                img_dict[name] = url
                img_dict[name.strip()] = url
                img_dict[name.replace('"', '')] = url
                
        return img_dict
        
    except FileNotFoundError:
        st.error(f"Файл не найден: {file_path}")
        return {}
    except Exception as e:
        st.error(f"Ошибка чтения файла {file_path}: {str(e)}")
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
        st.error(f"File {supply_path} not found.")
        return {}
    
# Функция для получения последнего непустого значения
def get_last_valid_price(df, item):
    # Получаем все непустые значения
    valid_prices = df[item].dropna()
    if len(valid_prices) > 0:
        return valid_prices.iloc[-1]
    return None

def main():
    # Load all data
    df, _ = load_data()
    supply_dict = load_supply_data()
    img_dict = load_image_data()
    default_img = "https://i.ibb.co/tpZ9HsSY/photo-2023-12-23-09-42-33.jpg"

    # Проверка соответствия имен
    items = [col for col in df.columns if col != 'timestamp']
    items_with_supply = [f"{item} (Supply: {int(supply_dict.get(item, 0))})" for item in items]
    display_to_original = dict(zip(items_with_supply, items))
    
    # Sidebar with filters
    with st.sidebar:
        st.header("Filters")
        
        selected_items_with_supply = st.multiselect(
            f"Select items (total: {len(items)})",
            items_with_supply,
            default=[items_with_supply[0]] if items_with_supply else []
        )
        
        selected_items = [display_to_original[item] for item in selected_items_with_supply]
        
        date_range = st.date_input(
            "Select period",
            value=(df['timestamp'].min().date(), df['timestamp'].max().date()),
            min_value=df['timestamp'].min().date(),
            max_value=df['timestamp'].max().date()
        )
        
        show_ma = st.checkbox("Show moving average", value=True)
        if show_ma:
            ma_period = st.slider("Moving average period (hours)", 1, 24, 6)

        # Создаем колонки для заголовка и процента
    title_col, percent_col = st.columns([2, 1])
    
    # Добавляем заголовок в левую колонку
    with title_col:
        st.title("Price History Analysis")

    # Check date_range
    if len(date_range) != 2:
        st.error("Please select two dates to define the period")
        return

    # Display chart and statistics
    if selected_items:
        mask = (df['timestamp'].dt.date >= date_range[0]) & (df['timestamp'].dt.date <= date_range[1])
        filtered_df = df.loc[mask]
        
        # Теперь добавляем процентное изменение в правую колонку
        with percent_col:
            if len(selected_items) == 1:
                item = selected_items[0]
                start_price = filtered_df[item].dropna().iloc[0] if not filtered_df[item].dropna().empty else None
                end_price = get_last_valid_price(filtered_df, item)
                
                if start_price is not None and end_price is not None:
                    percent_change = ((end_price - start_price) / start_price) * 100
                    color = "green" if percent_change >= 0 else "red"
                    arrow = "↑" if percent_change >= 0 else "↓"
                    st.markdown(f"""
                        <div style='text-align: right; padding-top: 1rem;'>
                            <span style='font-size: 32px; color: {color}; font-weight: bold;'>
                                {arrow} {abs(percent_change):.2f}%
                            </span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

    # Check date_range
    if len(date_range) != 2:
        st.error("Please select two dates to define the period")
        return

    # Display chart and statistics
    if selected_items:
        mask = (df['timestamp'].dt.date >= date_range[0]) & (df['timestamp'].dt.date <= date_range[1])
        filtered_df = df.loc[mask]
        
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
            xaxis_title="Time",
            yaxis_title="Price",
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
            
            # Calculate percentage change
            start_price = filtered_df[item].dropna().iloc[0] if not filtered_df[item].dropna().empty else None
            end_price = get_last_valid_price(filtered_df, item)

            img_col, stats_col = st.columns([0.5, 2])
            
            with img_col:
                # Сначала добавляем CSS для отступа
                st.markdown("""
                    <style>
                    [data-testid="stImage"] {
                        margin-top: -10px;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                
                # Ищем изображение с разными вариантами очистки имени
                item_clean = item.strip().strip('"')
                img_url = img_dict.get(item_clean, None)
                if img_url is None:
                    img_url = img_dict.get(item.strip(), None)
                if img_url is None:
                    img_url = img_dict.get(item.replace('"', '').strip(), None)
                if img_url is None:
                    img_url = default_img
                    st.warning(f"No image found for item: '{item}'")
                
                # Отображаем изображение один раз
                st.image(img_url, use_container_width=True)
                
            with stats_col:
                st.subheader(f"Statistics - {item}")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                current_price = get_last_valid_price(filtered_df, item)
                min_price = filtered_df[item].dropna().min() if not filtered_df[item].dropna().empty else None
                max_price = filtered_df[item].dropna().max() if not filtered_df[item].dropna().empty else None
                supply = supply_dict.get(item, 0)
                
                # Display metrics with responsive font size and theme-aware colors
                metric_style = """
                    <style>
                    .metric-container {
                        text-align: center;
                        padding: 0.5rem;
                    }
                    .metric-label {
                        font-size: 0.8rem;
                        color: var(--text-color-secondary);
                        margin-bottom: 0.3rem;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                    .metric-value {
                        font-size: 1rem;
                        font-weight: bold;
                        color: var(--text-color-primary);
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }

                    /* Адаптивные стили для разных размеров экрана */
                    @media (min-width: 1200px) {
                        .metric-label { font-size: 1rem; }
                        .metric-value { font-size: 1.2rem; }
                    }

                    @media (max-width: 768px) {
                        .metric-label { font-size: 0.7rem; }
                        .metric-value { font-size: 0.9rem; }
                    }

                    @media (max-width: 480px) {
                        .metric-label { font-size: 0.6rem; }
                        .metric-value { font-size: 0.8rem; }
                    }

                    /* Light theme colors */
                    [data-theme="light"] {
                        --text-color-primary: #0f0f0f;
                        --text-color-secondary: #888;
                    }

                    /* Dark theme colors */
                    [data-theme="dark"] {
                        --text-color-primary: #ffffff;
                        --text-color-secondary: #cccccc;
                    }
                    </style>
                """

                st.markdown(metric_style, unsafe_allow_html=True)

                # Add theme detection script
                theme_script = """
                    <script>
                        if (document.documentElement.classList.contains('dark')) {
                            document.documentElement.setAttribute('data-theme', 'dark');
                        } else {
                            document.documentElement.setAttribute('data-theme', 'light');
                        }
                    </script>
                """
                st.markdown(theme_script, unsafe_allow_html=True)

                # Custom metric display function remains the same
                def custom_metric(label, value):
                    return f"""
                    <div class="metric-container">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                    </div>
                    """                    
                
                # И обновите отображение метрик:
                def format_value(value):
                    if value is None:
                        return "Нет данных"
                    return f"{value:.2f}"


                col1.markdown(custom_metric("Current Price", format_value(current_price)), unsafe_allow_html=True)
                col2.markdown(custom_metric("Minimum Price", format_value(min_price)), unsafe_allow_html=True)
                col3.markdown(custom_metric("Maximum Price", format_value(max_price)), unsafe_allow_html=True)
                col4.markdown(custom_metric("Supply", f"{int(supply)}"), unsafe_allow_html=True)
                
if __name__ == "__main__":
    main()

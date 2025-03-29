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
    try:
        with open("data/img.csv", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        img_dict = {}
        for line in lines[1:]:  # skip header
            split_index = line.find("https://")
            if split_index != -1:
                name = line[:split_index].strip()
                img = line[split_index:].strip()
                img_dict[name] = img
                
        return img_dict
        
    except FileNotFoundError:
        st.error("File img.csv not found.")
        return {}
    except Exception as e:
        st.error(f"Error reading img.csv file: {str(e)}")
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

def main():
    # Load all data
    df, _ = load_data()
    supply_dict = load_supply_data()
    img_dict = load_image_data()
    default_img = "https://i.ibb.co/tpZ9HsSY/photo-2023-12-23-09-42-33.jpg"

    # Title and percentage change in one line
    col1, col2 = st.columns([2, 1])
    with col1:
        st.title("Price History Analysis")
    
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

    # Add percentage change after selected_items and date_range definition
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
            start_price = filtered_df[item].iloc[0]  # Price at start of period
            end_price = filtered_df[item].iloc[-1]   # Price at end of period
            price_change = end_price - start_price
            price_change_percent = (price_change / start_price) * 100

            img_col, stats_col = st.columns([1, 2])
            
            with img_col:
                img_url = img_dict.get(item, default_img)
                st.image(img_url, use_container_width=True)
            
            with stats_col:
                st.subheader(f"Statistics - {item}")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                current_price = filtered_df[item].iloc[-1]
                min_price = filtered_df[item].min()
                max_price = filtered_df[item].max()
                supply = supply_dict.get(item, 0)
                
                # Display metrics with responsive font size and theme-aware colors
                metric_style = """
                    <style>
                    .metric-container {
                        text-align: center;
                    }
                    .metric-label {
                        font-size: 1vw;
                        color: var(--text-color-secondary);
                        margin-bottom: 0.5vw;
                    }
                    .metric-value {
                        font-size: 1.5vw;
                        font-weight: bold;
                        color: var(--text-color-primary);
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

                col1.markdown(custom_metric("Current Price", f"{current_price:.2f}"), unsafe_allow_html=True)
                col2.markdown(custom_metric("Minimum Price", f"{min_price:.2f}"), unsafe_allow_html=True)
                col3.markdown(custom_metric("Maximum Price", f"{max_price:.2f}"), unsafe_allow_html=True)
                col4.markdown(custom_metric("Supply", f"{int(supply)}"), unsafe_allow_html=True)
                                
if __name__ == "__main__":
    main()

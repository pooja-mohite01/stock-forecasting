import streamlit as st
import numpy as np
import ta
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import os
from statsmodels.tsa.arima.model import ARIMA
import time
from contextlib import contextmanager
import itertools
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats.mstats import winsorize
import streamlit as st
import mysql.connector
import requests
import pandas as pd
import json
from hashlib import sha256
import os

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "YOUR API KEY"

# Function to create a secure database connection
def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="trendgaze_db"
    )

# Function to check if the user already exists
def user_exists(username):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user is not None

# Function to register a new user
def register_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = sha256(password.encode('utf-8')).hexdigest()
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
    conn.commit()
    cursor.close()
    conn.close()

# Function to check user credentials
def check_user_credentials(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = sha256(password.encode('utf-8')).hexdigest()
    cursor.execute("SELECT username FROM users WHERE username = %s AND password_hash = %s", (username, hashed_password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

def register_page():
    st.markdown("<h1>Create Your Account</h1>", unsafe_allow_html=True)

    with st.form("register_form"):
        st.markdown("<p style='color: #1565C0; text-align: center; margin-bottom: 2rem;'>Join TrendGaze to access real-time stock analysis and predictions</p>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Create a strong password")
        password_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("Register")
        with col2:
            login_redirect = st.form_submit_button("Already have an account?")

        if submit_button:
            if not username or not password:
                st.warning("Please fill in all fields.")
            elif password != password_confirm:
                st.error("Passwords do not match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long!")
            else:
                if user_exists(username):
                    st.error("Username already exists! Try logging in.")
                else:
                    register_user(username, password)
                    st.success("Registration successful! Redirecting to login...")
                    st.session_state.page = "login"
                    st.rerun()

        if login_redirect:
            st.session_state.page = "login"
            st.rerun()

def login_page():
    st.markdown("""
        <div style="text-align: center;">
            <h1>Welcome Back!</h1>
            <p style='color: #1565C0; text-align: center; margin-bottom: 2rem;'>
                Sign in to access your TrendGaze dashboard
            </p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("Sign In")
        with col2:
            register_redirect = st.form_submit_button("Create Account")

        if submit_button:
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                user = check_user_credentials(username, password)
                if user:
                    st.success(f"Welcome back, {username}!")
                    st.session_state.user = username
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials! Please try again.")

        if register_redirect:
            st.session_state.page = "register"
            st.rerun()

# Context manager for loading states
@contextmanager
def loading_state(message="Processing..."):
    with st.spinner(message):
        yield

st.set_page_config(page_title="Stock Market Analysis", layout="wide")


# Add custom CSS
st.markdown("""
    <style>
        /* Page Layout */
    .reportview-container {
        background: #d4a4ac;
        padding: 2.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        /* Text Colors */
        body {
            color: #18416b !important;
        }

        /* Card Styles */
        .stCard {
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            border: 1px solid rgba(0, 0, 0, 0.05) !important;
        }

        /* Button Styles */
        .stButton > button {
            background: #7caee1 !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            background: #9ec0f8 !important;
            transform: translateY(-1px) !important;
        }

        /* Alert Styles */
        .stAlert-success {
            background: linear-gradient(135deg, #9ec0f8, #7caee1) !important;
            color: white !important;
        }

        .stAlert-warning {
            background: linear-gradient(135deg, #d4a4ac, #acbca4) !important;
            color: white !important;
        }

        .stAlert-error {
            background: linear-gradient(135deg, #d4a4ac, #d4a4ac) !important;
            color: white !important;
        }

        /* Header Styles */
        .main-header {
            background: #7caee1 !important;
            color: white !important;
            padding: 1rem !important;
            border-radius: 10px !important;
            margin-bottom: 2rem !important;
        }

        .main-header h1 {
            margin: 0 !important;
            font-size: 2rem !important;
        }

        /* Sidebar Styles */
        .sidebar .sidebar-content {
            background: #272c3c !important;
            color: #7caee1 !important;
        }

        .sidebar .sidebar-content .stMarkdown {
            color: #7caee1 !important;
        }

        /* Chart Styles */
        .stPlotlyChart {
            background: white !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }

        /* Input Styles */
        .stTextInput > div > div > input {
            border-radius: 12px !important;
            padding: 0.75rem !important;
            border: 2px solid #acbca4 !important;
            transition: all 0.3s ease !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #7caee1 !important;
            box-shadow: 0 0 0 3px rgba(124, 174, 225, 0.2) !important;
            outline: none !important;
        }

        .stSelectbox > div > div {
            border-radius: 12px !important;
            padding: 0.75rem !important;
            border: 2px solid #acbca4 !important;
            transition: all 0.3s ease !important;
        }

        .stSelectbox > div > div:focus {
            border-color: #7caee1 !important;
            box-shadow: 0 0 0 3px rgba(124, 174, 225, 0.2) !important;
            outline: none !important;
        }
    </style>
""", unsafe_allow_html=True)

def dashboard_page():
    import requests
    import pandas as pd
    import streamlit as st

    # Check if user is logged in
    if 'user' not in st.session_state:
        st.session_state.user = None
        st.warning("Session expired. Please login again.")
        st.session_state.page = "login"
        st.rerun()
        return

    user = st.session_state.get('user')
    if user:
        st.title(f"Welcome, {user}!")
    else:
        st.warning("Please login first.")
        st.session_state.page = "login"
        st.rerun()
        return

    # Sidebar for navigation
    st.sidebar.header("Menu")
    selected_section = st.sidebar.selectbox(
        "Section",
        ["Stock Overview", "Stock Screener", "News", "Stock Predictions"],
        index=0
    )
    api_key = "YOUR_API_KEY"
    alpha_vantage_key = "YOUR_API_KEY"
    financial_modeling_prep_key = "YOUR API KEY "
    alpha_vantage_news_key = "YOUR API KEY "

    # Helper Functions
    @st.cache_data
    def get_stock_data(symbol, interval, api_key):
        base_url = "https://api.stockdata.org/v1/data/eod"
        url = f"{base_url}?symbols={symbol}&api_token={api_key}"

        try:
            response = requests.get(url)
            data = response.json()

            if "data" not in data:
                    st.error(f"Error fetching stock data: {data.get('error', {}).get('message', 'Unknown Error')}")
                    return pd.DataFrame()

            df = pd.DataFrame(data["data"])
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)

            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df = df.sort_index()

            return df

        except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return pd.DataFrame()
    @st.cache_data
    def get_top_gainers_losers(api_key):
        url = f"https://api.stockdata.org/v1/data/quote/list?api_token={api_key}"

        try:
            response = requests.get(url)
            data = response.json()

            if "data" in data:
                df = pd.DataFrame(data["data"])
                df["change_percent"] = df["change_pct"].astype(float)
                gainers = df.nlargest(5, "change_percent")[["ticker", "close", "change_percent"]]
                losers = df.nsmallest(5, "change_percent")[["ticker", "close", "change_percent"]]
                return gainers, losers
            else:
                return None, None

        except Exception as e:
            st.error(f"Error fetching gainers and losers: {str(e)}")
            return None, None
    @st.cache_data
    def get_historical_data(symbol, api_key):
        url = f"https://api.stockdata.org/v1/data/eod?symbols={symbol}&api_token={api_key}"

        try:
            response = requests.get(url)
            data = response.json()

            if "data" in data:
                df = pd.DataFrame(data["data"])
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                df = df.sort_index()
                    
                # Ensure column names match what ARIMA expects
                df = df["close"].to_frame()
                df.columns = ["Close"]
                    
                # Set business day frequency
                df = df.asfreq('B')  # Business day frequency
                df = df.fillna(method='ffill')  # Forward fill missing values
                    
                return df
            else:
                return None

        except Exception as e:
            st.error(f"Error fetching historical data: {str(e)}")
            return None
    @st.cache_data
    def fetch_stock_data(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                st.error("Failed to fetch data. Check your API Key or limit.")
                return []
        except Exception as e:
            st.error(f"Error: {e}")
            return []

    @st.cache_data
    def get_stock_data_alpha_vantage(symbol):
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={alpha_vantage_key}"
        response = requests.get(url)
            
        if response.status_code == 200:
            data = response.json()
            if "Symbol" in data:
                return data
            else:
                st.error("Invalid stock symbol or API limit reached.")
                return None
        else:
            st.error("Failed to fetch data. Check your API Key or API limits.")
            return None

    @st.cache_data
    def get_stock_quote_alpha_vantage(symbol):
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
        response = requests.get(url)
            
        if response.status_code == 200:
            data = response.json().get("Global Quote", {})
            return data
        return None

    # Function to fetch stock news
    @st.cache_data
    def get_stock_news(symbol):
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={alpha_vantage_news_key}"
        response = requests.get(url)
        data = response.json()
            
        if "feed" in data:
            return data["feed"][:5]  # Get top 5 latest news articles
        else:
            return []

    # Page Content
    if selected_section == "Stock Overview":
            # Header Section
            st.markdown("""
            
            .stSidebar {
            background-color: #f8f9fa !important;
            padding: 15px;
            border-radius: 10px;
                    }
            </style>
            

            
            """, unsafe_allow_html=True)
            st.markdown("""
            <style> border: 2px solid black;
                    padding: 7px;
            </style>
                        """, unsafe_allow_html=True)
            
            


            # Stock Selection in Stock Overview page
            st.subheader("Stock Selection")
            col1, col2 = st.columns(2)
            
            with col1:
                stock_options = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META", "NFLX", "NVDA"]
                selected_stock = st.selectbox("", stock_options, index=0)
            
            with col2:
                interval = st.selectbox("", ["1d", "1w", "1m"], index=0)

            data = get_stock_data(selected_stock, interval, api_key)

            if data.empty:
                st.stop()

            # Stock Price Metrics
            current_price = round(data['Close'].iloc[-1], 2)
            previous_price = round(data['Close'].iloc[-2], 2)
            price_change = round(current_price - previous_price, 2)
            percent_change = round((price_change / previous_price) * 100, 2)

            open_price = round(data['Open'].iloc[-1], 2)
            close_price = round(data['Close'].iloc[-1], 2)
            low_price = round(data['Low'].iloc[-1], 2)

            st.markdown("""
            <style>
                .metric {
                    background: white;
                    border: 2px solid #ddd; /* Light gray border */
                    border-radius: 10px; /* Rounded corners */
                    padding: 15px;
                    text-align: center;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1); /* Subtle shadow */
                    transition: all 0.3s ease;
                }

                .metric:hover {
                    border-color: #007BFF; /* Change border color on hover */
                    transform: scale(1.05); /* Slightly increase size */
                    box-shadow: 4px 4px 15px rgba(0, 0, 0, 0.2);
                    cursor:pointer;
                }
            </style>
        """, unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown("""
            <div class="metric">
                <h3>Current Price</h3>
                <p>${0}</p>
                <p class="delta">{1} ({2}%)</p>
            </div>
            """.format(current_price, price_change, percent_change), unsafe_allow_html=True)
            col2.markdown("""
            <div class="metric">
                <h3>Open Price</h3>
                <p>${0}</p>
            </div>
            """.format(open_price), unsafe_allow_html=True)
            col3.markdown("""
            <div class="metric">
                <h3>Low Price</h3>
                <p>${0}</p>
            </div>
            """.format(low_price), unsafe_allow_html=True)
            col4.markdown("""
            <div class="metric">
                <h3>Close Price</h3>
                <p>${0}</p>
            </div>
            """.format(close_price), unsafe_allow_html=True)

            # Candlestick Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'], name='Candlestick'
            ))
            fig.update_layout(title=f"{selected_stock} Candlestick Chart", xaxis_rangeslider_visible=False)
            
            st.plotly_chart(fig, use_container_width=True)

            # Stock Insights
            st.markdown("""
            <div class="card-container">
                <h2 class="section-header">Stock Insights</h2>
                <p>
                - <strong>Trend:</strong> Observing the candlestick patterns, the stock has shown recent <strong>bullish/bearish</strong> movement.<br>
                - <strong>Bullish</strong>: A market or stock is considered bullish when prices are rising or expected to rise.<br>
                - <strong>Bearish</strong>: A market or stock is considered bearish when prices are falling or expected to fall.<br>
                - <strong>Volatility:</strong> Large candlesticks indicate high volatility, while small ones suggest a steady trend.<br>
                - <strong>Price Action:</strong> The latest close price suggests market sentiment and potential future movement.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Historical vs. Current Price Comparison
            st.markdown("""
            <div class="section-header">
                Historical vs. Current Price for {0}
            </div>
            """.format(selected_stock), unsafe_allow_html=True)

            if not data.empty:
                historical_data = get_historical_data(selected_stock, api_key)

                if historical_data is not None and not historical_data.empty:
                    fig = px.line(
                        historical_data, x=historical_data.index, y="Close",
                        title=f"{selected_stock} Stock Price History",
                        labels={"Close": "Stock Price ($)"}
                    )
                    if current_price is not None and not pd.isna(current_price):
                        fig.add_hline(y=current_price, line_dash="dash", line_color="red",
                                    annotation_text=f"Current Price: ${current_price}",
                                    annotation_position="bottom right")

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ Unable to fetch historical data. Please check the stock symbol.")

            # Gainers and Losers
            st.markdown("""
            <div class="section-header">
                Stock Market Gainers & Losers
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 Refresh Data", key="refresh_data"):
                st.rerun()

            TOP_GAINERS_URL = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={financial_modeling_prep_key}"
            TOP_LOSERS_URL = f"https://financialmodelingprep.com/api/v3/stock_market/losers?apikey={financial_modeling_prep_key}"

            gainers_data = fetch_stock_data(TOP_GAINERS_URL)
            losers_data = fetch_stock_data(TOP_LOSERS_URL)

            if gainers_data and losers_data:
                gainers_df = pd.DataFrame(gainers_data)[["symbol", "name", "price", "change", "changesPercentage"]]
                losers_df = pd.DataFrame(losers_data)[["symbol", "name", "price", "change", "changesPercentage"]]

                gainers_df.columns = ["Symbol", "Company", "Price ($)", "Change ($)", "Change (%)"]
                losers_df.columns = ["Symbol", "Company", "Price ($)", "Change ($)", "Change (%)"]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("""
                    <div class="card-container">
                        <h3 class="subheader"> Top Gainers</h3>
                        {0}
                    </div>
                    """.format(gainers_df.to_html(index=False)), unsafe_allow_html=True)

                with col2:
                    st.markdown("""
                    <div class="card-container">
                        <h3 class="subheader"> Top Losers</h3>
                        {0}
                    </div>
                    """.format(losers_df.to_html(index=False)), unsafe_allow_html=True)
            else:
                st.warning("No data available. Check API limits or key.")

    elif selected_section == "Stock Screener":
        st.markdown('<div class="header-container">Stock Screener</div>', unsafe_allow_html=True)

            


        # Custom CSS for Styling
        st.markdown("""
            <style>
                /* Header Styling */
                .header-container {
                    background-color: #4A90E2;
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                    margin-bottom: 20px;
                }

                /* Stock Name Styling */
                .stock-title {
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }

                .stock-title img {
                    width: 30px;
                    height: 30px;
                }

                /* Stock Data Cards */
                .stock-card {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 10px;
                    text-align: center;
                }

                .stock-metric {
                    font-size: 18px;
                    font-weight: bold;
                    color: #222;
                }

                .stock-value {
                    font-size: 22px;
                    color: #007BFF;
                    font-weight: bold;
                }
            </style>
        """, unsafe_allow_html=True)

        # Sidebar for stock symbol input
        import streamlit as st

        # Function to get stock logo dynamically
        def get_stock_logo(symbol):
            return f"https://logo.clearbit.com/{symbol.lower()}.com"

        # Inject CSS
        st.markdown("""
        <style>
        /* Header Container */
        .header-container {
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            background-color: #4285F4;
            color: white;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        /* Stock Title */
        .stock-title {
            display: flex;
            align-items: center;
            font-size: 22px;
            font-weight: bold;
            color: #333;
            padding: 10px;
            border-bottom: 2px solid #ddd;
        }

        .stock-title img {
            width: 40px;
            height: 40px;
            margin-right: 10px;
            border-radius: 50%;
        }

        /* Stock Data Cards */
        .stock-card {
            background-color: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            cursor:pointer;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
            .stock-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }



        .stock-metric {
            font-size: 16px;
            font-weight: bold;
            color: #555;
            margin-bottom: 5px;
        }

        .stock-value {
            font-size: 18px;
            font-weight: bold;
            color: #007BFF;
        }
        </style>
        """, unsafe_allow_html=True)
        def safe_format_int(value):
            try:
                return f"${int(value):,}"
            except (ValueError, TypeError):
                return "N/A"

        def safe_format_float_percentage(value):
            try:
                return f"{float(value) * 100:.2f}%"
        
            except (ValueError, TypeError):
                return "N/A"

        # Sidebar for User Input
        symbol = st.sidebar.text_input("Enter Stock Symbol", "AAPL").upper()

        # ✅ Display the Stock Screener title **only once**

        if symbol:
            stock_overview = get_stock_data_alpha_vantage(symbol)
            stock_quote = get_stock_quote_alpha_vantage(symbol)

            if stock_overview and stock_quote:
                # Dynamically generate the stock logo URL
                stock_logo = get_stock_logo(symbol)

                # Stock Name with Dynamic Icon
                st.markdown(f"""
                    <div class="stock-title">
                        <img src="{stock_logo}" onerror="this.onerror=null; this.src='https://upload.wikimedia.org/wikipedia/commons/6/6f/Stock_market_graph.svg';"> 
                        {stock_overview['Name']} ({stock_overview['Symbol']})
                    </div>
                """, unsafe_allow_html=True)

                # Stock Data Display with Columns
                col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Day Range</div><div class="stock-value">{stock_quote.get("04. low", "N/A")} - {stock_quote.get("03. high", "N/A")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Market Cap</div><div class="stock-value">{safe_format_int(stock_overview.get("MarketCapitalization"))}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">P/E Ratio</div><div class="stock-value">{stock_overview.get("PERatio", "N/A")}</div></div>', unsafe_allow_html=True)

            with col2:
                st.markdown(f'<div class="stock-card"><div class="stock-metric">52-Week Range</div><div class="stock-value">{stock_overview.get("52WeekLow", "N/A")} - {stock_overview.get("52WeekHigh", "N/A")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Sector</div><div class="stock-value">{stock_overview.get("Sector", "N/A")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Dividend Yield</div><div class="stock-value">{safe_format_float_percentage(stock_overview.get("DividendYield"))}</div></div>', unsafe_allow_html=True)

            with col3:
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Beta Value</div><div class="stock-value">{stock_overview.get("Beta", "N/A")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Debt-to-Equity Ratio</div><div class="stock-value">{stock_overview.get("DebtToEquity", "N/A")}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stock-card"><div class="stock-metric">Return on Equity (ROE)</div><div class="stock-value">{safe_format_float_percentage(stock_overview.get("ReturnOnEquityTTM"))}</div></div>', unsafe_allow_html=True)


        else:
            st.warning("No data available. Please check the stock symbol or API limits.")



    elif selected_section == "News":
            st.markdown("""
            <div class="main-header">
                <h1>Live News & Twitter Trends</h1>
            </div>
            """, unsafe_allow_html=True)
            
            # Stock symbol input
            symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA):")

            if symbol:
                news = get_stock_news(symbol)
                
                if news:
                    for article in news:
                        st.markdown(f"### 📌 {article['title']}")
                        st.write(f"**Source:** {article['source']} | 🕒 {article['time_published']}")
                        st.write(f"📖 {article['summary']}")
                        st.markdown(f"[🔗 Read more]({article['url']})", unsafe_allow_html=True)
                        
                        # Display news image if available
                        if article["banner_image"]:
                            st.image(article["banner_image"], width=600)

                        st.markdown("---")  # Separator between news articles
                else:
                    st.warning("⚠️ No news found. Try another stock symbol.")

    elif selected_section == "Stock Predictions":
        st.markdown("""
        <div class="main-header">
            <h1>Stock Price Predictions</h1>
        </div>
        """, unsafe_allow_html=True)

            # API configuration
        api_key = "YOUR_API_KEY"
        base_url = "https://www.alphavantage.co/query"

        def fetch_stock_data(symbol):
            """Fetch stock data from Alpha Vantage API."""
            try:
                # Fetch data from Alpha Vantage
                url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={api_key}&datatype=csv'
                df = pd.read_csv(url)
                
                # Convert date column to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Convert numeric columns to float
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Rename columns for consistency
                df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)
                
                # Sort by date
                df = df.sort_index()
                
                # Get last 2 years of data
                df = df[df.index >= df.index[-1] - pd.DateOffset(years=2)]
                
                # Drop rows with NaN values
                df = df.dropna()
                
                # Ensure data types are correct
                df['Open'] = df['Open'].astype(float)
                df['High'] = df['High'].astype(float)
                df['Low'] = df['Low'].astype(float)
                df['Close'] = df['Close'].astype(float)
                df['Volume'] = df['Volume'].astype(int)
                
                # Winsorize data to reduce the effect of outliers
                df['Close'] = winsorize(df['Close'], limits=[0.01, 0.01])
                
                # Add technical indicators and features
                df = add_features(df)
                
                return df
            except Exception as e:
                print(f"Error fetching data for {symbol}: {str(e)}")
                return None

        def detect_outliers_iqr(data, column):
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outlier_indices = data[(data[column] < lower_bound) | (data[column] > upper_bound)].index
            print(f"Detected {len(outlier_indices)} outliers in '{column}' using the IQR method.")
            return outlier_indices

        def interpolate_outliers(data, column, outlier_indices, method='linear'):
            if len(outlier_indices) > 0:
                data.loc[outlier_indices, column] = np.nan
                data[column] = data[column].interpolate(method=method)
                print(f"Interpolated {len(outlier_indices)} outliers in '{column}' using {method} interpolation.")

        def check_no_outliers_after_interpolation(data, column):
            outlier_indices_after = detect_outliers_iqr(data, column)
            if len(outlier_indices_after) == 0:
                print(f"No outliers detected in '{column}' after interpolation.")
                return True
            else:
                print(f"{len(outlier_indices_after)} outliers still present in '{column}' after interpolation.")
                return False

        def adf_test(series, column_name):
            print(f"\nPerforming ADF stationarity test on '{column_name}'...")
            result = adfuller(series.dropna())
            adf_stat = result[0]
            p_value = result[1]
            print(f"ADF Statistic: {adf_stat}")
            print(f"p-value: {p_value}")

            if p_value < 0.05:
                print(f"'{column_name}' is stationary (p-value < 0.05).")
                return True
            else:
                print(f"'{column_name}' is not stationary (p-value >= 0.05).")
                return False

        def plot_acf_pacf(data, column):
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 1, 1)
            plot_acf(data[column].dropna(), lags=40, ax=plt.gca(), color='blue')
            plt.title(f'ACF Plot - {column}')
            plt.subplot(2, 1, 2)
            plot_pacf(data[column].dropna(), lags=40, ax=plt.gca(), color='red')
            plt.title(f'PACF Plot - {column}')
            plt.tight_layout()
            plt.show()

        def calculate_accuracy_metrics(actual, predicted):
            """Calculate various accuracy metrics for the model."""
            # Calculate Mean Absolute Error (MAE)
            mae = mean_absolute_error(actual, predicted)
            
            # Calculate Mean Squared Error (MSE)
            mse = mean_squared_error(actual, predicted)
            
            # Calculate Root Mean Squared Error (RMSE)
            rmse = np.sqrt(mse)
            
            # Calculate Mean Absolute Percentage Error (MAPE)
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100
            
            # Calculate R-squared (R²)
            r2 = r2_score(actual, predicted)
            
            # Calculate Mean Absolute Scaled Error (MASE)
            # Using the in-sample mean absolute error as the scaling factor
            in_sample_mae = mean_absolute_error(actual[:-1], actual[1:])
            mase = mae / in_sample_mae
            
            return {
                'MAE': mae,
                'MSE': mse,
                'RMSE': rmse,
                'MAPE': mape,
                'R2': r2,
                'MASE': mase
            }

        def add_features(df):
            """Add technical indicators and features to enhance the model."""
            # Moving Averages
            df['MA_20'] = df['Close'].rolling(window=20).mean()
            df['MA_50'] = df['Close'].rolling(window=50).mean()
            df['MA_200'] = df['Close'].rolling(window=200).mean()
            
            # RSI
            df['RSI_14'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
            
            # MACD
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            
            # Volume indicators
            df['Volume_MA_20'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA_20'].replace(0, 1)
            
            # Volatility
            df['ATR_14'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
            
            # Returns
            df['Return'] = df['Close'].pct_change()
            df['Return_1'] = df['Return'].shift(1)
            df['Return_2'] = df['Return'].shift(2)
            
            # Drop rows with NaN values
            df = df.dropna()
            
            return df

        def optimize_arima_parameters(df):
            """Optimize ARIMA parameters using grid search."""
            p = range(0, 5)
            d = range(0, 3)
            q = range(0, 5)
            
            pdq = list(itertools.product(p, d, q))
            seasonal_pdq = [(x[0], x[1], x[2], 5) for x in list(itertools.product(p, d, q))]
            
            best_aic = float("inf")
            best_params = None
            best_seasonal_params = None
            
            for param in pdq:
                for param_seasonal in seasonal_pdq:
                    try:
                        mod = ARIMA(df['Close'],
                                order=param,
                                seasonal_order=param_seasonal,
                                enforce_stationarity=False,
                                enforce_invertibility=False)
                        
                        results = mod.fit()
                        
                        if results.aic < best_aic:
                            best_aic = results.aic
                            best_params = param
                            best_seasonal_params = param_seasonal
                            
                    except:
                        continue
            
            return best_params, best_seasonal_params

        def main():
            # Get stock symbol
            stock_symbol = "AAPL"  # Default to Apple stock
            print(f"\nAnalyzing {stock_symbol} stock data...")

            # Fetch and process data
            df = fetch_stock_data(stock_symbol)
            if df is None:
                raise Exception(f" Data could not be fetched for {stock_symbol}. Please check the symbol and try again.")

            # Print data overview
            print("\n--- Sample of Fetched Data ---")
            print(df.head())

            # Detect and handle outliers
            outlier_indices_iqr = detect_outliers_iqr(df, 'Close')
            if len(outlier_indices_iqr) > 0:
                interpolate_outliers(df, 'Close', outlier_indices_iqr, method='linear')
                check_no_outliers_after_interpolation(df, 'Close')

            # Check stationarity and apply differencing if needed
            is_stationary = adf_test(df['Close'], 'Close')
            target_column = 'Close'

            if not is_stationary:
                df['Close_diff1'] = df['Close'].diff().dropna()
                is_stationary = adf_test(df['Close_diff1'], 'Close_diff1')

                if not is_stationary:
                    df['Close_diff2'] = df['Close_diff1'].diff().dropna()
                    is_stationary = adf_test(df['Close_diff2'], 'Close_diff2')

                    if is_stationary:
                        print("\nUsing 'Close_diff2' for modeling.")
                        target_column = 'Close_diff2'
                    else:
                        print("\nSecond Differencing did not make the data stationary.")
                        print("\nConsider other transformations or models.")
                else:
                    print("\nUsing 'Close_diff1' for modeling.")
                    target_column = 'Close_diff1'

            # Plot ACF and PACF
            plot_acf_pacf(df, target_column)

            # Use simple ARIMA(2,1,2) model
            print("\nUsing ARIMA(2,1,2) model...")
            model = ARIMA(df['Close'], order=(2,1,2))
            model_fit = model.fit()

            # Make predictions
            pred = model_fit.predict(start=len(df)-30, end=len(df)-1, typ='levels').rename('ARIMA Predictions')
            pred.index = df.index[-30:]

            # Calculate accuracy metrics
            print("\nModel Accuracy Metrics:")
            metrics = calculate_accuracy_metrics(df['Close'][-30:], pred)
            for metric, value in metrics.items():
                if metric == 'MAPE':
                    print(f"{metric}: {value:.2f}%")
                elif metric == 'R2':
                    print(f"{metric}: {value:.4f}")
                else:
                    print(f"{metric}: {value:.2f}")

            # Make future predictions
            future_steps = 30
            future_index = pd.date_range(start=df.index[-1], periods=future_steps + 1, freq='D')[1:]
            
            # Get predictions with confidence intervals
            forecast = model_fit.get_forecast(steps=future_steps)
            pred = forecast.predicted_mean
            conf_int = forecast.conf_int()
            
            # Create DataFrame for predictions
            predictions_df = pd.DataFrame({
                'Date': future_index,
                'Predicted_Price': pred.values,
                'Lower_Bound': conf_int.iloc[:, 0].values,
                'Upper_Bound': conf_int.iloc[:, 1].values
            })
            predictions_df.to_csv(f'{stock_symbol}_predictions.csv', index=False)
            print(f"\nPredictions saved to {stock_symbol}_predictions.csv")

            # Print predicted mean values
            print("\nPredicted Mean Prices for the Next 30 Days:")
            print(predictions_df[['Date', 'Predicted_Price']].head(5))  # Show first 5 days
            print(f"\nAverage Predicted Price for the Next 30 Days: ${predictions_df['Predicted_Price'].mean():.2f}")

            # Plot future predictions with confidence intervals
            plt.figure(figsize=(15, 8))
            plt.plot(df.index, df['Close'], label='Historical', color='blue', alpha=0.7)
            plt.plot(future_index, pred, label='Predicted', color='green', linestyle='--')
            plt.fill_between(future_index, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color='green', alpha=0.2, label='95% Confidence Interval')
            
            # Add vertical line to separate historical and predicted data
            plt.axvline(x=df.index[-1], color='red', linestyle='--', alpha=0.7)
            
            plt.title(f'{stock_symbol} Stock Price Predictions', fontsize=16)
            plt.xlabel('Date', fontsize=14)
            plt.ylabel('Stock Price', fontsize=14)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{stock_symbol}_predictions_plot.png')
            plt.show()

        if __name__ == "__main__":
            main()
        # Stock Predictions Content
        st.subheader("Stock Price Prediction Dashboard")

        symbol = st.text_input("Enter Stock Symbol (e.g., AAPL)", "AAPL")

        if st.button("Generate Predictions"):
            with st.spinner("Analyzing stock data..."):
                df = fetch_stock_data(symbol)
                if df is not None:
                    st.write("Stock Data Sample:")
                    st.dataframe(df.head())
                else:
                    st.error("Failed to fetch stock data.")
                print("\nModel Accuracy Metrics:")
                # Use simple ARIMA(2,1,2) model
                print("\nUsing ARIMA(2,1,2) model...")
                model = ARIMA(df['Close'], order=(2,1,2))
                model_fit = model.fit()

            # Make predictions
                pred = model_fit.predict(start=len(df)-30, end=len(df)-1, typ='levels').rename('ARIMA Predictions')
                pred.index = df.index[-30:]
                metrics = calculate_accuracy_metrics(df['Close'][-30:], pred)
                for metric, value in metrics.items():
                    if metric == 'MAPE':
                        print(f"{metric}: {value:.2f}%")
                    elif metric == 'R2':
                        print(f"{metric}: {value:.4f}")
                    else:
                        print(f"{metric}: {value:.2f}")
                        
                        # Make future predictions
                        future_steps = 30
                        future_index = pd.date_range(start=df.index[-1], periods=future_steps + 1, freq='D')[1:]
                
            # Get predictions with confidence intervals
                        forecast = model_fit.get_forecast(steps=future_steps)
                        pred = forecast.predicted_mean
                        conf_int = forecast.conf_int()
                
            # Create DataFrame for predictions
                        predictions_df = pd.DataFrame({
                                'Date': future_index,
                                'Predicted_Price': pred.values,
                                'Lower_Bound': conf_int.iloc[:, 0].values,
                                'Upper_Bound': conf_int.iloc[:, 1].values
                        })
                
            print(predictions_df[['Date', 'Predicted_Price']].head(5))  # Show first 5 days
            st.write("Predictions for the next 30 days:",predictions_df)
            print(f"\nAverage Predicted Price for the Next 30 Days: ${predictions_df['Predicted_Price'].mean():.2f}")
            st.write("Accuracy of the Model",metrics)
            

def main():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        .stApp {
            background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
        }
        
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.9);
            padding: 2rem 3rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.4);
            max-width: 450px !important;
            margin: 2rem auto;
        }

        div[data-baseweb="input"] {
            background-color: rgba(255, 255, 255, 0.8) !important;
            border-radius: 10px !important;
            border: 1px solid #90CAF9 !important;
            padding: 0.5rem !important;
        }

        div[data-baseweb="input"]:focus-within {
            border-color: #1976D2 !important;
            box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2) !important;
        }

        div[data-baseweb="input"] input {
            color: #1565C0 !important;
            font-size: 1rem !important;
        }

        button[kind="primaryFormSubmit"] {
            background: linear-gradient(45deg, #2196F3, #1976D2) !important;
            color: white !important;
            border: none !important;
            padding: 0.8rem 2rem !important;
            font-size: 1.1rem !important;
            border-radius: 10px !important;
            width: 100% !important;
            margin-top: 1rem !important;
            transition: all 0.3s ease !important;
        }

        button[kind="secondaryFormSubmit"] {
            background: rgba(255, 255, 255, 0.9) !important;
            color: #1976D2 !important;
            border: 2px solid #1976D2 !important;
            padding: 0.8rem 2rem !important;
            font-size: 1.1rem !important;
            border-radius: 10px !important;
            width: 100% !important;
            margin-top: 1rem !important;
            transition: all 0.3s ease !important;
        }

        button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 15px rgba(25, 118, 210, 0.3) !important;
        }

        h1 {
            color: #1565C0 !important;
            font-size: 2.5rem !important;
            text-align: center;
            margin-bottom: 2rem !important;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
        }

        label {
            color: #1976D2 !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
            margin-bottom: 0.5rem !important;
        }

        p {
            color: #1565C0 !important;
            text-align: center;
        }

        div[data-baseweb="notification"] {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid #90CAF9 !important;
            border-radius: 10px !important;
            margin: 1rem 0 !important;
            color: #1565C0 !important;
        }

        .element-container div[data-testid="stMarkdownContainer"] div.stSuccess {
            background-color: rgba(232, 245, 233, 0.95) !important;
            color: #2E7D32 !important;
            border: 1px solid #81C784;
        }

        .element-container div[data-testid="stMarkdownContainer"] div.stWarning {
            background-color: rgba(255, 244, 229, 0.95) !important;
            color: #F57C00 !important;
            border: 1px solid #FFB74D;
        }

        .element-container div[data-testid="stMarkdownContainer"] div.stError {
            background-color: rgba(255, 235, 238, 0.95) !important;
            color: #C62828 !important;
            border: 1px solid #E57373;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

    # Render appropriate page
    if st.session_state.user is None:
        if st.session_state.page == "register":
            register_page()
        else:
            login_page()
    else:
        dashboard_page()


if __name__ == "__main__":
    main()

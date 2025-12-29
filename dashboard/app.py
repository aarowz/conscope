#!/usr/bin/env python3
"""
ConScope Dashboard - Streamlit Application

Real-time dashboard for monitoring ticket prices, alerts, and system metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ConScope - Ticket Price Monitor",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection pool
@st.cache_resource
def get_connection_pool():
    """Get database connection pool."""
    try:
        return pool.SimpleConnectionPool(
            1, 10,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "conscope"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "password")
        )
    except Exception as e:
        st.error(f"Error creating connection pool: {e}")
        return None


def get_db_connection():
    """Get a connection from the pool."""
    connection_pool = get_connection_pool()
    if not connection_pool:
        return None
    try:
        return connection_pool.getconn()
    except Exception as e:
        st.error(f"Error getting connection from pool: {e}")
        return None


def put_db_connection(conn):
    """Return a connection to the pool."""
    connection_pool = get_connection_pool()
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except:
            pass


def get_events():
    """Get list of all tracked events."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = """
            SELECT DISTINCT event_id, event_name, venue, event_date
            FROM events
            ORDER BY event_date DESC
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def get_price_history(event_id: str = None, hours: int = 24):
    """Get price history for events."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        # Build query with proper interval syntax
        # Use a longer default window if no recent data (for testing)
        query = f"""
            SELECT 
                ph.id as price_id,
                ph.event_id,
                e.event_name,
                e.venue,
                ph.section,
                ph.row,
                ph.seat,
                ph.price,
                ph.fees,
                ph.total_price,
                ph.source,
                ph.timestamp,
                ph.listing_url
            FROM price_history ph
            JOIN events e ON ph.event_id = e.event_id
            WHERE ph.timestamp >= NOW() - INTERVAL '{hours} hours'
        """
        
        params = []
        if event_id:
            query += " AND ph.event_id = %s"
            params.append(event_id)
        
        query += " ORDER BY ph.timestamp DESC LIMIT 10000"
        
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching price history: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def get_recent_alerts(limit: int = 20):
    """Get recent price drop alerts."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = """
            SELECT 
                a.alert_id,
                a.event_id,
                e.event_name,
                e.venue,
                a.section,
                a.row,
                a.seat,
                a.old_price,
                a.new_price,
                a.drop_amount,
                a.drop_percent,
                a.source,
                a.alert_timestamp,
                a.listing_url
            FROM price_drop_alerts a
            JOIN events e ON a.event_id = e.event_id
            ORDER BY a.alert_timestamp DESC
            LIMIT %s
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        return df
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def get_price_stats(event_id: str = None):
    """Get price statistics."""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        if event_id:
            query = """
                SELECT 
                    COUNT(*) as total_listings,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    COUNT(DISTINCT source) as num_sources
                FROM price_history
                WHERE event_id = %s
                AND timestamp >= NOW() - INTERVAL '48 hours'
            """
            cursor = conn.cursor()
            cursor.execute(query, [event_id])
        else:
            query = """
                SELECT 
                    COUNT(*) as total_listings,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    COUNT(DISTINCT source) as num_sources
                FROM price_history
                WHERE timestamp >= NOW() - INTERVAL '48 hours'
            """
            cursor = conn.cursor()
            cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return {
                'total_listings': result[0] or 0,
                'avg_price': float(result[1]) if result[1] else 0,
                'min_price': float(result[2]) if result[2] else 0,
                'max_price': float(result[3]) if result[3] else 0,
                'num_sources': result[4] or 0
            }
        return {}
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return {}
    finally:
        put_db_connection(conn)


def main():
    """Main dashboard application."""
    # Header
    st.title("🎫 ConScope - Real-Time Ticket Price Monitor")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("📊 Dashboard Controls")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Time range selector
    hours = st.sidebar.selectbox(
        "Time Range",
        [6, 12, 24, 48, 72, 168],
        index=3,  # Default to 48 hours
        help="Show data from the last N hours"
    )
    
    # Event selector
    events_df = get_events()
    if not events_df.empty:
        event_options = ["All Events"] + events_df['event_name'].tolist()
        selected_event = st.sidebar.selectbox("Select Event", event_options)
        event_id = None if selected_event == "All Events" else events_df[events_df['event_name'] == selected_event]['event_id'].iloc[0] if selected_event in events_df['event_name'].values else None
    else:
        selected_event = "All Events"
        event_id = None
    
    # Main content
    if events_df.empty:
        st.warning("⚠️ No events found in database. Start a producer to begin tracking prices.")
        return
    
    # Statistics cards
    st.subheader(f"📈 Price Statistics (Last {hours} Hours)")
    stats = get_price_stats(event_id)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Listings", f"{stats.get('total_listings', 0):,}")
    
    with col2:
        avg_price = stats.get('avg_price', 0)
        st.metric("Average Price", f"${avg_price:.2f}" if avg_price > 0 else "N/A")
    
    with col3:
        min_price = stats.get('min_price', 0)
        st.metric("Lowest Price", f"${min_price:.2f}" if min_price > 0 else "N/A")
    
    with col4:
        max_price = stats.get('max_price', 0)
        st.metric("Highest Price", f"${max_price:.2f}" if max_price > 0 else "N/A")
    
    with col5:
        st.metric("Sources", stats.get('num_sources', 0))
    
    st.markdown("---")
    
    # Price history chart
    st.subheader("📊 Price History")
    price_df = get_price_history(event_id, hours)
    
    if not price_df.empty:
        # Price over time chart
        price_df['timestamp'] = pd.to_datetime(price_df['timestamp'])
        price_df = price_df.sort_values('timestamp')
        
        # Group by timestamp and source for cleaner chart
        chart_df = price_df.groupby(['timestamp', 'source'])['price'].mean().reset_index()
        
        fig = px.line(
            chart_df,
            x='timestamp',
            y='price',
            color='source',
            title=f"Average Price Over Time ({hours}h)",
            labels={'price': 'Price ($)', 'timestamp': 'Time'},
            markers=True
        )
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Price distribution by source
        col1, col2 = st.columns(2)
        
        with col1:
            source_price_df = price_df.groupby('source')['price'].agg(['mean', 'min', 'max']).reset_index()
            source_price_df.columns = ['Source', 'Average', 'Minimum', 'Maximum']
            st.dataframe(source_price_df, use_container_width=True)
        
        with col2:
            # Price distribution histogram
            fig_hist = px.histogram(
                price_df,
                x='price',
                color='source',
                title="Price Distribution",
                labels={'price': 'Price ($)', 'count': 'Frequency'},
                nbins=30
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No price data available for the selected time range.")
    
    st.markdown("---")
    
    # Recent alerts
    st.subheader("🚨 Recent Price Drop Alerts")
    alerts_df = get_recent_alerts(limit=20)
    
    if not alerts_df.empty:
        # Filter by selected event if applicable
        if event_id:
            alerts_df = alerts_df[alerts_df['event_id'] == event_id]
        
        # Format alerts for display
        display_alerts = alerts_df[[
            'event_name', 'venue', 'section', 'row', 'seat',
            'old_price', 'new_price', 'drop_amount', 'drop_percent',
            'source', 'alert_timestamp'
        ]].copy()
        
        display_alerts.columns = [
            'Event', 'Venue', 'Section', 'Row', 'Seat',
            'Old Price', 'New Price', 'Drop ($)', 'Drop (%)',
            'Source', 'Time'
        ]
        
        # Format prices
        display_alerts['Old Price'] = display_alerts['Old Price'].apply(lambda x: f"${x:.2f}")
        display_alerts['New Price'] = display_alerts['New Price'].apply(lambda x: f"${x:.2f}")
        display_alerts['Drop ($)'] = display_alerts['Drop ($)'].apply(lambda x: f"${x:.2f}")
        display_alerts['Drop (%)'] = display_alerts['Drop (%)'].apply(lambda x: f"{x:.1f}%")
        
        # Format timestamp
        display_alerts['Time'] = pd.to_datetime(display_alerts['Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        st.dataframe(display_alerts, use_container_width=True, hide_index=True)
        
        # Alerts chart
        alerts_df['alert_timestamp'] = pd.to_datetime(alerts_df['alert_timestamp'])
        alerts_by_time = alerts_df.groupby(alerts_df['alert_timestamp'].dt.floor('H')).size().reset_index()
        alerts_by_time.columns = ['Time', 'Alerts']
        
        fig_alerts = px.bar(
            alerts_by_time,
            x='Time',
            y='Alerts',
            title="Price Drop Alerts Over Time",
            labels={'Alerts': 'Number of Alerts', 'Time': 'Time'}
        )
        fig_alerts.update_layout(height=300)
        st.plotly_chart(fig_alerts, use_container_width=True)
    else:
        st.info("No price drop alerts yet. Alerts will appear here when prices drop.")
    
    st.markdown("---")
    
    # Footer
    st.markdown("### 📝 System Status")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Database:** Connected ✅")
    
    with col2:
        total_events = len(events_df)
        st.write(f"**Tracked Events:** {total_events}")
    
    with col3:
        if not price_df.empty:
            latest_update = price_df['timestamp'].max()
            if pd.notna(latest_update):
                st.write(f"**Latest Update:** {latest_update.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Fallback: get latest timestamp from database
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(timestamp) FROM price_history")
                    result = cursor.fetchone()
                    cursor.close()
                    if result and result[0]:
                        st.write(f"**Latest Update:** {result[0].strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass
                finally:
                    put_db_connection(conn)


if __name__ == "__main__":
    main()


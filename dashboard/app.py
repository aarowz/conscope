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


def get_price_stats(event_id: str = None, hours: int = 48):
    """Get price statistics for the selected time window."""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        interval_str = f"{hours} hours"
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
                AND timestamp >= NOW() - %s::interval
            """
            cursor.execute(query, [event_id, interval_str])
        else:
            query = """
                SELECT 
                    COUNT(*) as total_listings,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    COUNT(DISTINCT source) as num_sources
                FROM price_history
                WHERE timestamp >= NOW() - %s::interval
            """
            cursor.execute(query, [interval_str])
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


def get_top_price_drops(hours: int = 24, limit: int = 6, event_id: str = None, venue: str = None):
    """Get top price drops using the price_drop_alerts table."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        interval_str = f"{hours} hours"
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
            WHERE a.alert_timestamp >= NOW() - %s::interval
        """
        params = [interval_str]
        if event_id:
            query += " AND a.event_id = %s"
            params.append(event_id)
        if venue:
            query += " AND e.venue = %s"
            params.append(venue)
        query += """
            ORDER BY a.drop_percent DESC
            LIMIT %s
        """
        params.append(limit)
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error fetching top price drops: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def render_hero_filters(events_df: pd.DataFrame):
    """Render hero search/filters and return selected filters."""
    # Hero heading + central search bar (ticketdata-style)
    st.markdown(
        "<h1 style='text-align:center; font-size:2.4rem; margin-bottom:1rem;'>"
        "Track Ticket Prices for Your Favorite Events"
        "</h1>",
        unsafe_allow_html=True,
    )

    # Styling for hero search bar (pill-shaped, prominent)
    st.markdown(
        """
        <style>
        input[placeholder="Team, Artist, or Venue"] {
            border-radius: 999px;
            padding: 0.75rem 1.25rem;
            font-size: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Central search bar with width similar to ticketdata hero
    left_pad, center_col, right_pad = st.columns([1.5, 3, 1.5])
    with center_col:
        search_query = st.text_input(
            "",
            value=st.session_state.get("hero_search_query", ""),
            placeholder="Team, Artist, or Venue",
            label_visibility="collapsed",
        )

    st.session_state["hero_search_query"] = search_query

    # Optionally filter events shown in the Event dropdown based on search
    if not events_df.empty and search_query:
        events_for_select = events_df[
            events_df["event_name"].str.contains(search_query, case=False, na=False)
        ]
        # If no matches, fall back to all events
        if events_for_select.empty:
            events_for_select = events_df
    else:
        events_for_select = events_df

    # For now, skip additional filters below the search bar
    location = "All locations"
    hours = st.session_state.get("hero_hours", 48)
    event_id = None

    # Persist defaults in session state for other sections
    st.session_state["hero_location"] = location
    st.session_state["hero_hours"] = hours
    st.session_state["hero_event_name"] = "All events"
    st.session_state["hero_event_id"] = event_id

    return location, hours, event_id


def render_top_price_drops(hours: int, event_id: str, location: str):
    """Render Top Price Drops section."""
    st.markdown("---")
    st.subheader("🚨 Top Price Drops")

    venue_filter = None
    if location and location != "All locations":
        venue_filter = location

    drops_df = get_top_price_drops(hours=hours, limit=6, event_id=event_id, venue=venue_filter)
    if drops_df.empty:
        st.info("No recent price drops in the selected window.")
        return

    cols = st.columns(3)
    for idx, (_, row) in enumerate(drops_df.iterrows()):
        col = cols[idx % 3]
        with col:
            st.markdown(
                f"**{row['event_name']}**  \n"
                f"{row['venue']}  \n"
                f"Section {row['section']}, Row {row['row']}, Seat {row['seat']}"
            )
            # Image placeholder between seat info and price line
            st.image(
                "https://via.placeholder.com/320x180?text=Event+Image",
                use_column_width=True,
            )
            st.write(
                f"Old: ${row['old_price']:.2f} → New: ${row['new_price']:.2f} "
                f"(**-{row['drop_amount']:.2f} / {row['drop_percent']:.1f}%**)"
            )
            st.caption(
                f"Source: {row['source']} • "
                f"{pd.to_datetime(row['alert_timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if row.get("listing_url"):
                st.markdown(f"[View listing]({row['listing_url']})")


def render_detail_view(events_df: pd.DataFrame, event_id: str, hours: int):
    """Deprecated: detailed view removed from main layout."""
    return None


def render_status_footer(events_df: pd.DataFrame, price_df: pd.DataFrame, hours: int):
    """Render compact system status footer."""
    st.markdown("---")
    st.markdown("### 📝 System Status")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Database:** Connected ✅")

    with col2:
        total_events = len(events_df)
        st.write(f"**Tracked Events:** {total_events}")

    with col3:
        if price_df is not None and not price_df.empty:
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


def render_dashboard_controls():
    """Render dashboard controls (auto-refresh, etc.) in the main area. Call at end of page."""
    st.markdown("---")
    st.markdown("### 📊 Dashboard Controls")

    query_params = st.experimental_get_query_params()
    refresh_param = query_params.get("refresh", [None])[0] if query_params.get("refresh") else None
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = (refresh_param == "10")

    auto_refresh = st.checkbox(
        "Auto-refresh (10s)",
        value=st.session_state.auto_refresh,
        key="auto_refresh_cb",
    )
    st.session_state.auto_refresh = auto_refresh

    if auto_refresh and refresh_param != "10":
        st.experimental_set_query_params(refresh="10")
        st.rerun()
    if not auto_refresh and refresh_param == "10":
        st.experimental_set_query_params()
        st.rerun()
    if auto_refresh:
        st.components.v1.html(
            """
            <script>
            setTimeout(function() {
                var url = new URL(window.parent.location.href);
                url.searchParams.set('refresh', '10');
                window.parent.location.href = url.toString();
            }, 10000);
            </script>
            <span style="font-size:12px;color:#888;">Refreshing in 10s…</span>
            """,
            height=28,
        )


def main():
    """Main dashboard application."""
    # Load events once for the page
    events_df = get_events()

    # Logo and branding at top left
    logo_col, _ = st.columns([1, 5])
    with logo_col:
        st.markdown(
            "<span style='font-size:1.8rem; font-weight:700;'>🎫 ConScope</span>",
            unsafe_allow_html=True,
        )
    # Hero filters (header-style controls)
    location, hours, event_id = render_hero_filters(events_df)

    # Highlights & quick views
    render_top_price_drops(hours=hours, event_id=event_id, location=location)

    # Detailed view removed; keep price_df for status footer as None
    price_df = None

    # Status footer
    render_status_footer(events_df, price_df, hours)

    # Dashboard controls (last section)
    render_dashboard_controls()


if __name__ == "__main__":
    main()


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

# Query params: prefer st.query_params (1.30+), fall back to experimental (1.29 and earlier)
def _get_query_param(key: str):
    if hasattr(st, "query_params"):
        return st.query_params.get(key)
    q = st.experimental_get_query_params()
    v = q.get(key)
    if v is None:
        return None
    return v[0] if isinstance(v, list) else v


def _set_query_params(params: dict):
    if hasattr(st, "query_params"):
        st.query_params.from_dict(params)
    else:
        st.experimental_set_query_params(**params)


def _clear_query_param(key: str):
    if hasattr(st, "query_params"):
        q = st.query_params.to_dict()
        q.pop(key, None)
        st.query_params.from_dict(q)
    else:
        q = st.experimental_get_query_params()
        q.pop(key, None)
        st.experimental_set_query_params(**{k: (v[0] if isinstance(v, list) else v) for k, v in q.items()})


def render_home_logo(button_key: str):
    """Render clickable ConScope logo that returns to home page."""
    if st.button("🎫 ConScope", key=button_key):
        _clear_query_param("event_id")
        _clear_query_param("search")
        st.session_state.pop("active_search_query", None)
        st.session_state["active_page"] = "home"
        st.rerun()

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


def get_event_by_id(event_id: str):
    """Return one event row (event_id, event_name, venue, event_date, city, state) or None."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        query = """
            SELECT event_id, event_name, venue, event_date, city, state
            FROM events WHERE event_id = %s
        """
        df = pd.read_sql_query(query, conn, params=[event_id])
        if df.empty:
            return None
        return df.iloc[0]
    except Exception as e:
        st.error(f"Error fetching event: {e}")
        return None
    finally:
        put_db_connection(conn)


def get_current_getin(event_id: str, lookback_hours: int = 24):
    """Min price (get-in) for event in last lookback_hours. Returns float or None."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT MIN(price) FROM price_history
            WHERE event_id = %s AND timestamp >= NOW() - %s::interval
            """,
            [event_id, f"{lookback_hours} hours"],
        )
        row = cursor.fetchone()
        cursor.close()
        if row and row[0] is not None:
            return float(row[0])
        return None
    except Exception as e:
        st.error(f"Error fetching get-in: {e}")
        return None
    finally:
        put_db_connection(conn)


def get_getin_change_3d(event_id: str):
    """Return (current_getin, previous_getin, percent_change) or None if insufficient data."""
    current = get_current_getin(event_id, lookback_hours=24)
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT MIN(price) FROM price_history
            WHERE event_id = %s
              AND timestamp >= NOW() - INTERVAL '96 hours'
              AND timestamp < NOW() - INTERVAL '72 hours'
            """,
            [event_id],
        )
        row = cursor.fetchone()
        cursor.close()
        if not row or row[0] is None or current is None:
            return None
        previous = float(row[0])
        if previous == 0:
            return None
        percent_change = ((current - previous) / previous) * 100
        return (current, previous, percent_change)
    except Exception as e:
        st.error(f"Error fetching 3d change: {e}")
        return None
    finally:
        put_db_connection(conn)


def get_getin_price_series(event_id: str, hours: int = None):
    """Return DataFrame with timestamp and get-in (min) price per time bucket for chart."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    try:
        if hours is not None:
            query = """
                SELECT date_trunc('hour', timestamp) AS bucket, MIN(price) AS getin_price
                FROM price_history
                WHERE event_id = %s AND timestamp >= NOW() - %s::interval
                GROUP BY date_trunc('hour', timestamp)
                ORDER BY bucket
            """
            df = pd.read_sql_query(query, conn, params=[event_id, f"{hours} hours"])
        else:
            query = """
                SELECT date_trunc('day', timestamp) AS bucket, MIN(price) AS getin_price
                FROM price_history
                WHERE event_id = %s
                GROUP BY date_trunc('day', timestamp)
                ORDER BY bucket
            """
            df = pd.read_sql_query(query, conn, params=[event_id])
        return df
    except Exception as e:
        st.error(f"Error fetching price series: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def search_events(query: str, limit: int = 200):
    """Search events by name, venue, city, or state."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    try:
        q = f"%{query.strip()}%"
        sql = """
            SELECT event_id, event_name, venue, event_date, city, state
            FROM events
            WHERE event_name ILIKE %s
               OR venue ILIKE %s
               OR COALESCE(city, '') ILIKE %s
               OR COALESCE(state, '') ILIKE %s
            ORDER BY event_date ASC
            LIMIT %s
        """
        return pd.read_sql_query(sql, conn, params=[q, q, q, q, limit])
    except Exception as e:
        st.error(f"Error searching events: {e}")
        return pd.DataFrame()
    finally:
        put_db_connection(conn)


def get_event_last_updated(event_id: str):
    """Latest price_history timestamp for an event."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(timestamp) FROM price_history WHERE event_id = %s",
            [event_id],
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None
    finally:
        put_db_connection(conn)


def derive_performer_name(event_name: str):
    """Best-effort performer extraction from event name."""
    if not event_name:
        return "TBD"
    name = str(event_name)
    if name.startswith("test_"):
        core = name.replace("test_", "", 1)
        parts = core.split("_")
        if parts and parts[-1].isdigit():
            parts = parts[:-1]
        cleaned = " ".join(parts).strip()
        return cleaned.title() if cleaned else name
    return name


def format_relative_time(value):
    """Convert timestamp into compact relative text."""
    if value is None or pd.isna(value):
        return "—"
    try:
        ts = pd.Timestamp(value)
        delta = pd.Timestamp.now() - ts
        seconds = max(int(delta.total_seconds()), 0)
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60} min ago"
        if seconds < 86400:
            return f"{seconds // 3600} hours ago"
        return f"{seconds // 86400} days ago"
    except Exception:
        return "—"


def render_search_results_page(search_query: str):
    """Render search results page with filter controls and event rows."""
    search_query = (search_query or "").strip()
    if search_query:
        st.session_state["active_search_query"] = search_query
        st.session_state["active_page"] = "search"
    if not search_query:
        st.info("Enter a search term to find events.")
        if st.button("Back to home", key="search_back_home_empty"):
            _clear_query_param("search")
            st.session_state.pop("active_search_query", None)
            st.session_state["active_page"] = "home"
            st.rerun()
        return

    # Header with compact search aligned to the top-right
    logo_col, spacer_col, search_col = st.columns([1.2, 4.6, 2.2])
    with logo_col:
        render_home_logo("logo_search_page")
    with spacer_col:
        st.write("")
    with search_col:
        with st.form("search_results_refine_form", clear_on_submit=False):
            refined = st.text_input(
                "Search",
                value=search_query,
                placeholder="Team, Artist, or Venue",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Search")
        if submitted:
            refined = (refined or "").strip()
            if refined:
                _set_query_params({"search": refined})
                st.session_state["active_search_query"] = refined
                st.session_state["active_page"] = "search"
                st.rerun()
            else:
                _clear_query_param("search")
                st.session_state.pop("active_search_query", None)
                st.session_state["active_page"] = "home"
                st.rerun()
    st.markdown(f"## {search_query} ticket prices")

    events_df = search_events(search_query)
    match_count = len(events_df)
    st.caption(f"Tracking {search_query} ticket prices for {match_count} matching events.")

    left_filters, right_filters = st.columns([2, 2])
    with left_filters:
        scope = st.radio("Scope", ["Upcoming", "Past", "All"], horizontal=True, label_visibility="collapsed")
    with right_filters:
        day_filter = st.selectbox("Days of Week", ["All days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        time_filter = st.radio("Times", ["All Times", "Day Only", "Night Only"], horizontal=True, label_visibility="collapsed")

    if events_df.empty:
        st.info("No events found for this search. Try a broader term.")
        if st.button("Back to home", key="search_back_home_no_results"):
            _clear_query_param("search")
            st.session_state.pop("active_search_query", None)
            st.session_state["active_page"] = "home"
            st.rerun()
        return

    events_df["event_date"] = pd.to_datetime(events_df["event_date"], errors="coerce")
    now = pd.Timestamp.now()

    if scope == "Upcoming":
        filtered = events_df[events_df["event_date"] >= now]
    elif scope == "Past":
        filtered = events_df[events_df["event_date"] < now]
    else:
        filtered = events_df

    if day_filter != "All days":
        filtered = filtered[filtered["event_date"].dt.day_name() == day_filter]

    if time_filter == "Day Only":
        filtered = filtered[(filtered["event_date"].dt.hour >= 6) & (filtered["event_date"].dt.hour < 18)]
    elif time_filter == "Night Only":
        filtered = filtered[(filtered["event_date"].dt.hour < 6) | (filtered["event_date"].dt.hour >= 18)]

    if filtered.empty:
        st.info("No events match the selected filters.")
        return

    st.caption(f"Showing {len(filtered)} event(s)")
    st.markdown("---")

    header_cols = st.columns([2.3, 1.7, 2.0, 1.8, 1.0, 1.2, 1.3, 1.4])
    headers = ["Event", "Date", "Performer", "Venue", "City", "3 Day Change", "Get-In", "Last Updated"]
    for col, label in zip(header_cols, headers):
        col.markdown(f"**{label}**")

    for _, row in filtered.iterrows():
        eid = str(row.get("event_id", ""))
        current_getin = get_current_getin(eid, lookback_hours=24) if eid else None
        change_3d = get_getin_change_3d(eid) if eid else None
        change_text = f"{change_3d[2]:+.1f}%" if change_3d is not None else "—"
        updated_text = format_relative_time(get_event_last_updated(eid)) if eid else "—"
        date_text = row["event_date"].strftime("%a, %m/%d/%Y %I:%M %p") if pd.notna(row["event_date"]) else "—"
        city_text = row.get("city") if pd.notna(row.get("city")) and row.get("city") else "TBD"
        venue_text = row.get("venue") or "TBD"
        performer_text = derive_performer_name(row.get("event_name"))
        getin_text = f"${current_getin:.0f}" if current_getin is not None else "—"

        cols = st.columns([2.3, 1.7, 2.0, 1.8, 1.0, 1.2, 1.3, 1.4])
        cols[0].write(row.get("event_name", "—"))
        cols[1].write(date_text)
        cols[2].write(performer_text)
        cols[3].write(venue_text)
        cols[4].write(city_text)
        cols[5].write(change_text)
        cols[6].write(getin_text)
        cols[7].write(updated_text)

        if eid and st.button("View details", key=f"search_view_details_{eid}"):
            _set_query_params({"event_id": eid})
            st.session_state["active_page"] = "detail"
            st.rerun()

        st.caption(f"Last updated: {updated_text}")
        st.markdown("---")


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
        with st.form("hero_search_form", clear_on_submit=False):
            search_query = st.text_input(
                "",
                value=st.session_state.get("hero_search_query", ""),
                placeholder="Team, Artist, or Venue",
                label_visibility="collapsed",
            )
            search_submitted = st.form_submit_button("Search")
        if search_submitted:
            query_value = (search_query or "").strip()
            if query_value:
                _set_query_params({"search": query_value})
                st.session_state["active_search_query"] = query_value
                st.session_state["active_page"] = "search"
                st.rerun()

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
            eid = row.get("event_id")
            if eid is not None:
                eid = str(eid)
                aid = row.get("alert_id", idx)
                if st.button("View details", key=f"view_details_{eid}_{aid}"):
                    _set_query_params({"event_id": eid})
                    st.rerun()
            if row.get("listing_url"):
                st.markdown(f"[View listing]({row['listing_url']})")


def _get_listing_url_for_event(event_id: str):
    """Return a listing_url for this event from price_history or price_drop_alerts if available."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT listing_url FROM price_history WHERE event_id = %s AND listing_url IS NOT NULL AND listing_url != '' LIMIT 1",
            [event_id],
        )
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        cursor.execute(
            "SELECT listing_url FROM price_drop_alerts WHERE event_id = %s AND listing_url IS NOT NULL AND listing_url != '' LIMIT 1",
            [event_id],
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None
    finally:
        put_db_connection(conn)


def render_event_detail_page(event_id: str):
    """Render the in-app event detail view (header, overview, 4 cards, chart, buy section, back link)."""
    event = get_event_by_id(event_id)
    if event is None:
        st.warning("Event not found.")
        if st.button("← Back to home"):
            _clear_query_param("event_id")
            st.rerun()
        return

    # --- Header ---
    logo_col, _, right_col = st.columns([1, 3, 1])
    with logo_col:
        render_home_logo("logo_detail_page")
    with right_col:
        st.button("Log in", help="Coming soon")

    # --- Back to home ---
    def go_home():
        _clear_query_param("event_id")
        st.rerun()

    if st.button("← Back to home", key="back_top"):
        go_home()
    st.markdown("---")

    # --- Event overview ---
    st.markdown(f"## {event['event_name']}")
    venue = event.get("venue") or "—"
    city = event.get("city")
    state = event.get("state")
    if pd.notna(city) and pd.notna(state) and city and state:
        location = f"{venue} | {city}, {state}"
    else:
        location = venue
    ed = event.get("event_date")
    if pd.notna(ed):
        try:
            dt = pd.to_datetime(ed)
            date_str = dt.strftime("%a, %b. %d %Y %I:%M %p") if hasattr(dt, "strftime") else str(ed)
        except Exception:
            date_str = str(ed)
    else:
        date_str = "—"
    st.caption(f"{event['event_name']} | {location} | {date_str}")
    st.markdown("Share: [Share](/#) [Facebook](/#) [X](/#)")
    st.markdown("---")

    # --- Four metric cards ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        current_getin = get_current_getin(event_id, lookback_hours=24)
        if current_getin is not None:
            st.metric("Current Get-In Price", f"${current_getin:.2f}", help="Lowest listed price (incl. fees)")
        else:
            st.metric("Current Get-In Price", "—", help="No recent data")
    with c2:
        change_3d = get_getin_change_3d(event_id)
        if change_3d is not None:
            _, _, pct = change_3d
            st.metric("3 Day Price Change", f"{pct:+.1f}%", help="vs get-in 72–96h ago")
        else:
            st.metric("3 Day Price Change", "—", help="No 3-day data")
    with c3:
        ed = event.get("event_date")
        if pd.notna(ed):
            try:
                target = pd.Timestamp(ed)
                now = pd.Timestamp.now()
                delta = target - now
                if delta.total_seconds() <= 0:
                    st.metric("Time To Event", "Event ended")
                else:
                    d = delta.days
                    h, r = divmod(int(delta.total_seconds()), 3600)
                    m, s = divmod(r, 60)
                    st.metric("Time To Event", f"{d}d {h}h {m}m")
            except Exception:
                st.metric("Time To Event", "—")
        else:
            st.metric("Time To Event", "—")
    with c4:
        st.markdown("**Price Forecast**")
        st.markdown("Forecast closed")
        st.caption("Coming soon")

    # --- Action buttons ---
    st.button("Watch", help="Save to watchlist (coming soon)")
    st.button("Set a Price Alert", help="Get notified when price drops (coming soon)")
    st.markdown("---")

    # --- Price history ---
    st.subheader("Price History")
    st.caption("Historical get-in price for this event.")
    range_options = {"1 Day": 24, "3 Days": 72, "1 Week": 168, "1 Month": 720, "6 Months": 4320, "All Time": None}
    key = "event_detail_range"
    if key not in st.session_state:
        st.session_state[key] = "1 Week"
    chosen = st.radio("Time range", list(range_options.keys()), horizontal=True, key=key)
    hours = range_options[chosen]
    df_series = get_getin_price_series(event_id, hours=hours)
    if not df_series.empty and "bucket" in df_series.columns and "getin_price" in df_series.columns:
        fig = px.line(df_series, x="bucket", y="getin_price", labels={"bucket": "Date", "getin_price": "Get-in price ($)"})
        fig.update_layout(showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price history for this range.")
    st.checkbox("Show Zones", value=False, help="Coming soon")
    st.markdown("---")

    # --- Ticket purchase ---
    st.subheader("Get tickets")
    listing_url = _get_listing_url_for_event(event_id) or "#"
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("Buy on Vivid", listing_url if "vivid" in str(listing_url).lower() else "https://www.vividseats.com/")
        st.link_button("Buy on StubHub", listing_url if "stubhub" in str(listing_url).lower() else "https://www.stubhub.com/")
    with c2:
        st.markdown("Also check the primary (box office)")
        st.link_button("Buy on Ticketmaster", "https://www.ticketmaster.com/")
    st.markdown("---")
    if st.button("← Back to home", key="back_bottom"):
        go_home()


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


def main():
    """Main dashboard application."""
    # Query-param routing: event detail page
    eid = _get_query_param("event_id")
    if eid:
        st.session_state["active_page"] = "detail"
        render_event_detail_page(str(eid))
        return
    search_query = _get_query_param("search")
    if search_query:
        st.session_state["active_search_query"] = str(search_query)
        st.session_state["active_page"] = "search"
        render_search_results_page(str(search_query))
        return
    persisted_search = st.session_state.get("active_search_query")
    if st.session_state.get("active_page") == "search" and persisted_search:
        render_search_results_page(str(persisted_search))
        return

    # Load events once for the page
    st.session_state["active_page"] = "home"
    events_df = get_events()

    # Logo and branding at top left
    logo_col, _ = st.columns([1, 5])
    with logo_col:
        render_home_logo("logo_home_page")
    # Hero filters (header-style controls)
    location, hours, event_id = render_hero_filters(events_df)

    # Highlights & quick views
    render_top_price_drops(hours=hours, event_id=event_id, location=location)

    # Detailed view removed; keep price_df for status footer as None
    price_df = None

    # Status footer
    render_status_footer(events_df, price_df, hours)


if __name__ == "__main__":
    main()


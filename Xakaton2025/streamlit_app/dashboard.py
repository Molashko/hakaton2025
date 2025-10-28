import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
STREAMLIT_TITLE = "🎯 Executor Balancer Dashboard"

def init_session_state():
    """Initialize session state variables"""
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True

def make_api_request(endpoint: str, method: str = "GET", data: dict = None):
    """Make API request with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=5)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None

def get_distribution_stats():
    """Get current distribution statistics"""
    return make_api_request("/v1/distribution/stats")

def get_executors():
    """Get list of executors"""
    return make_api_request("/v1/executors")

def get_tasks():
    """Get recent tasks"""
    return make_api_request("/ais/tasks?limit=50")

def get_assignments():
    """Get recent assignments"""
    return make_api_request("/ais/assignments")

def generate_test_tasks(count: int = 10):
    """Generate test tasks"""
    tasks_created = 0
    for i in range(count):
        task_data = {
            "external_id": f"TEST_{int(time.time())}_{i}",
            "parameters": {
                "priority": "normal",
                "category": "test",
                "source": "dashboard"
            },
            "weight": 1
        }
        
        response = make_api_request("/v1/tasks", "POST", task_data)
        if response:
            tasks_created += 1
    
    return tasks_created

def create_executor(name: str, daily_limit: int = 100):
    """Create new executor"""
    executor_data = {
        "name": name,
        "parameters": {
            "skills": ["general"],
            "experience": "medium"
        },
        "active": True,
        "daily_limit": daily_limit
    }
    
    return make_api_request("/v1/executors", "POST", executor_data)

def sync_executors():
    """Sync executors with external AIS"""
    return make_api_request("/v1/executors/cache-sync", "POST")

def reset_daily_counts():
    """Reset daily assignment counts"""
    return make_api_request("/v1/admin/reset-daily-counts", "POST")

def export_kpi_excel():
    """Export KPI to Excel"""
    try:
        response = requests.get(f"{API_BASE_URL}/v1/exports/kpi?format=excel", timeout=10)
        response.raise_for_status()
        
        # Save file
        filename = f"kpi_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        return filename
    except Exception as e:
        st.error(f"Export error: {e}")
        return None

def main():
    st.set_page_config(
        page_title=STREAMLIT_TITLE,
        page_icon="🎯",
        layout="wide"
    )
    
    init_session_state()
    
    st.title(STREAMLIT_TITLE)
    st.markdown("---")
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (seconds)", 1, 30, 5)
            if st.button("🔄 Refresh Now"):
                st.session_state.last_update = datetime.now()
                st.rerun()
        else:
            if st.button("🔄 Refresh Now"):
                st.session_state.last_update = datetime.now()
                st.rerun()
        
        st.markdown("---")
        
        # Test data generation
        st.header("🧪 Test Data")
        test_count = st.number_input("Number of test tasks", 1, 100, 10)
        if st.button("📝 Generate Test Tasks"):
            with st.spinner("Generating test tasks..."):
                created = generate_test_tasks(test_count)
                st.success(f"Created {created} test tasks")
                st.session_state.last_update = datetime.now()
                st.rerun()
        
        # Executor management
        st.header("👥 Executors")
        if st.button("🔄 Sync Executors"):
            with st.spinner("Syncing executors..."):
                result = sync_executors()
                if result:
                    st.success(f"Synced {result.get('synced_executors', 0)} executors")
        
        if st.button("🔄 Reset Daily Counts"):
            with st.spinner("Resetting counts..."):
                result = reset_daily_counts()
                if result:
                    st.success("Daily counts reset")
        
        # New executor form
        with st.expander("➕ Add Executor"):
            with st.form("new_executor"):
                name = st.text_input("Executor Name")
                daily_limit = st.number_input("Daily Limit", 1, 1000, 100)
                
                if st.form_submit_button("Create Executor"):
                    if name:
                        result = create_executor(name, daily_limit)
                        if result:
                            st.success(f"Created executor: {name}")
                    else:
                        st.error("Please enter executor name")
        
        st.markdown("---")
        
        # Export controls
        st.header("📊 Export")
        if st.button("📈 Export KPI Excel"):
            with st.spinner("Exporting KPI..."):
                filename = export_kpi_excel()
                if filename:
                    st.success(f"Exported to {filename}")
    
    # Main dashboard content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Distribution Overview")
        
        # Get distribution stats
        stats = get_distribution_stats()
        
        if stats:
            # Key metrics
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Total Tasks", stats.get('total_tasks', 0))
            
            with metric_col2:
                st.metric("Active Executors", stats.get('total_executors', 0))
            
            with metric_col3:
                mae = stats.get('mae')
                if mae:
                    st.metric("MAE Fairness", f"{float(mae):.3f}")
                else:
                    st.metric("MAE Fairness", "N/A")
            
            with metric_col4:
                total_assigned = sum(a.get('assigned_today', 0) for a in stats.get('assignments', []))
                st.metric("Total Assigned Today", total_assigned)
            
            # Distribution chart
            assignments = stats.get('assignments', [])
            if assignments:
                df_assignments = pd.DataFrame(assignments)
                
                # Bar chart for executor utilization
                fig = px.bar(
                    df_assignments,
                    x='name',
                    y='utilization',
                    title="Executor Utilization",
                    labels={'utilization': 'Utilization %', 'name': 'Executor'},
                    color='utilization',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_layout(
                    xaxis_tickangle=-45,
                    yaxis=dict(range=[0, 1])
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table
                st.subheader("📋 Executor Details")
                display_df = df_assignments[['name', 'assigned_today', 'daily_limit', 'utilization']].copy()
                display_df['utilization'] = display_df['utilization'].apply(lambda x: f"{x:.1%}")
                display_df.columns = ['Executor', 'Assigned Today', 'Daily Limit', 'Utilization']
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No executor data available")
        else:
            st.error("Failed to load distribution stats")
    
    with col2:
        st.header("📈 Recent Activity")
        
        # Recent tasks
        tasks = get_tasks()
        if tasks:
            st.subheader("Recent Tasks")
            df_tasks = pd.DataFrame(tasks[:10])  # Show last 10
            if not df_tasks.empty:
                df_tasks['created_at'] = pd.to_datetime(df_tasks['created_at']).dt.strftime('%H:%M:%S')
                st.dataframe(
                    df_tasks[['external_id', 'status', 'created_at']],
                    use_container_width=True,
                    hide_index=True
                )
        
        # Recent assignments
        assignments = get_assignments()
        if assignments:
            st.subheader("Recent Assignments")
            df_assignments = pd.DataFrame(assignments[:10])  # Show last 10
            if not df_assignments.empty:
                df_assignments['assigned_at'] = pd.to_datetime(df_assignments['assigned_at']).dt.strftime('%H:%M:%S')
                st.dataframe(
                    df_assignments[['executor_name', 'assigned_at']],
                    use_container_width=True,
                    hide_index=True
                )
    
    # Auto-refresh logic
    if st.session_state.auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()

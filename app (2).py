import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# 1. PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Corner&Co. Strategic Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. DATA LOADING & ROBUST CLEANING (OPTIMIZED FOR GITHUB PATHS)
# ==============================================================================
@st.cache_data
def load_and_prepare_data():
    # GITHUB DEPLOYMENT RULE: Keep files in your repository's root folder 
    # and call them by their precise file names (case-sensitive!)
    sales_file = "cornerco_sales (1).csv"
    enquiries_file = "cornerco_enquiries.csv"
    
    sales = pd.read_csv(sales_file)
    enquiries = pd.read_csv(enquiries_file)
    
    # Clean column headers to protect against trailing whitespace KeyErrors
    sales.columns = sales.columns.str.strip()
    enquiries.columns = enquiries.columns.str.strip()
    
    # Process Sales Data types
    sales['date'] = pd.to_datetime(sales['date'])
    sales['item_name'] = sales['item_name'].astype(str).str.lower().str.strip()
    sales['total_revenue'] = sales['quantity'] * sales['unit_price']
    
    # Process Enquiries Data types
    enquiries['date'] = pd.to_datetime(enquiries['date'])
    
    # Aggregate sales to a daily framework first to avoid data duplication
    daily_sales = sales.groupby('date').agg(
        daily_revenue=('total_revenue', 'sum'),
        daily_transactions=('receipt_id', 'nunique')
    ).reset_index()
    
    # Execute precise daily Left Merge matching the project notebook configuration
    merged_daily = pd.merge(daily_sales, enquiries, on='date', how='left').fillna(0)
    
    return sales, enquiries, merged_daily

try:
    df_sales, df_enquiries, df_merged = load_and_prepare_data()
except Exception as e:
    st.error(f"❌ File Load Failure. Ensure your dataset filenames match exactly in your GitHub repository. Error details: {e}")
    st.stop()

# ==============================================================================
# 3. GLOBAL FILTER SIDEBAR
# ==============================================================================
st.sidebar.title("📊 Strategic Controls")
st.sidebar.markdown("Filter the business view globally.")

min_date = df_sales['date'].min().to_pydatetime()
max_date = df_sales['date'].max().to_pydatetime()
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)

all_ages = sorted(df_sales['customer_age_group'].dropna().unique())
selected_ages = st.sidebar.multiselect("Customer Age Groups", options=all_ages, default=all_ages)

max_dist = float(df_sales['customer_distance_km'].max())
selected_distance = st.sidebar.slider("Customer Distance Radius (km)", 0.0, max_dist, (0.0, max_dist))

# Dynamic multi-dimensional filtering cascades across your analytics layers
filtered_sales = df_sales[
    (df_sales['date'] >= start_dt) & (df_sales['date'] <= end_dt) &
    (df_sales['customer_age_group'].isin(selected_ages)) &
    (df_sales['customer_distance_km'].between(selected_distance[0], selected_distance[1]))
]

filtered_daily = df_merged[
    (df_merged['date'] >= start_dt) & (df_merged['date'] <= end_dt)
]

# ==============================================================================
# 4. DASHBOARD HEADER & STRATEGIC RECOMMENDATION
# ==============================================================================
st.title("💼 Corner&Co. — Omnichannel Investment Strategy")
st.markdown("### Evaluating Unmet Digital Demand Beyond the Cash Register")

st.info(
    "💡 **Consultant Recommendation:** **INVEST NOW.** While current online transactions sit near 0% "
    "due to an infrastructure block, out-of-store delivery requests and online order attempts represent a substantial "
    "untapped market, particularly among high-value digital-ready cohorts traveling long distances."
)
st.markdown("---")

# ==============================================================================
# 5. EXECUTION KPI SUMMARY CARDS
# ==============================================================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Captured Revenue", value=f"${filtered_sales['total_revenue'].sum():,.2f}")
with col2:
    st.metric(label="Explicit Delivery Requests", value=f"{int(filtered_daily['delivery_requests'].sum()):,}")
with col3:
    st.metric(label="Blocked Online Order Attempts", value=f"{int(filtered_daily['online_orders_attempted'].sum()):,}")
with col4:
    st.metric(label="Peak Friction Walkouts", value=f"{int(filtered_daily['customers_turned_away_peak'].sum()):,}")

st.markdown("---")

# ==============================================================================
# 6. SYSTEM TABS & INTERACTIVE PLOTLY VISUALIZATIONS
# ==============================================================================
tab1, tab2, tab3 = st.tabs(["📈 Unmet Demand & Operations", "👥 Customer Profiling", "📦 Inventory Performance"])

with tab1:
    st.subheader("The Demand vs. Infrastructure Gap")
    
    fig_demand = go.Figure()
    fig_demand.add_trace(go.Scatter(x=filtered_daily['date'], y=filtered_daily['delivery_requests'],
                                    mode='lines', name='Delivery Requests', line=dict(color='#1f77b4', width=2)))
    fig_demand.add_trace(go.Scatter(x=filtered_daily['date'], y=filtered_daily['online_orders_attempted'],
                                    mode='lines', name='Attempted Web Orders', line=dict(color='#ff7f0e', width=2)))
    fig_demand.update_layout(
        title="Daily Unmet Digital Demand Trends",
        xaxis_title="Timeline",
        yaxis_title="Count of Customer Signals",
        hovermode="x unified",
        template="plotly_white"
    )
    st.plotly_chart(fig_demand, use_container_width=True)
    
    st.subheader("Store Front Bottlenecks")
    c1, c2 = st.columns(2)
    with c1:
        hourly_tx = filtered_sales.groupby('hour')['receipt_id'].nunique().reset_index()
        fig_hours = px.bar(hourly_tx, x='hour', y='receipt_id', 
                           title="Transaction Volume by Hour of Day",
                           labels={'hour': 'Hour (24h format)', 'receipt_id': 'Number of Sales'},
                           color_discrete_sequence=['#2ca02c'])
        fig_hours.update_layout(template="plotly_white")
        st.plotly_chart(fig_hours, use_container_width=True)
        
    with c2:
        fig_walk = px.box(filtered_daily, y='customers_turned_away_peak', 
                          title="Daily Customer Loss Distribution During Peaks",
                          labels={'customers_turned_away_peak': 'Customers Left Due to Queues'},
                          color_discrete_sequence=['#d62728'])
        fig_walk.update_layout(template="plotly_white")
        st.plotly_chart(fig_walk, use_container_width=True)

with tab2:
    st.subheader("Target Audience Readiness Profile")
    c3, c4 = st.columns(2)
    with c3:
        age_mix = filtered_sales.groupby('customer_age_group')['receipt_id'].nunique().reset_index()
        fig_age = px.pie(age_mix, values='receipt_id', names='customer_age_group', 
                         title="Customer Base Age Group Allocation", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_age, use_container_width=True)
        
    with c4:
        fig_dist = px.histogram(filtered_sales, x='customer_distance_km', nbins=20,
                                title="Customer Traveling Distance Distribution",
                                labels={'customer_distance_km': 'Distance to Store (km)'},
                                color_discrete_sequence=['#9467bd'])
        fig_dist.update_layout(template="plotly_white", yaxis_title="Transaction Frequency")
        st.plotly_chart(fig_dist, use_container_width=True)

with tab3:
    st.subheader("Product Catalogue Analytics")
    
    rank_metric = st.radio("Rank Inventory By:", options=["Units Sold Volume", "Revenue Generated"], horizontal=True)
    
    product_performance = filtered_sales.groupby('item_name').agg(
        units_sold=('quantity', 'sum'),
        revenue=('total_revenue', 'sum')
    ).reset_index()
    
    if rank_metric == "Units Sold Volume":
        top_products = product_performance.sort_values(by='units_sold', ascending=False).head(10)
        fig_prod = px.bar(top_products, x='units_sold', y='item_name', orientation='h',
                          title="Top 10 Products by True Volume Sold",
                          labels={'units_sold': 'Units Sold', 'item_name': 'Cleaned Item Name'},
                          color='units_sold', color_continuous_scale='Blues')
    else:
        top_products = product_performance.sort_values(by='revenue', ascending=False).head(10)
        fig_prod = px.bar(top_products, x='revenue', y='item_name', orientation='h',
                          title="Top 10 Products by Total Revenue Generation",
                          labels={'revenue': 'Total Revenue ($)', 'item_name': 'Cleaned Item Name'},
                          color='revenue', color_continuous_scale='Greens')
        
    fig_prod.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_white")
    st.plotly_chart(fig_prod, use_container_width=True)

# ==============================================================================
# 7. SYSTEM LEDGER VERIFICATION LOG
# ==============================================================================
st.markdown("---")
with st.expander("🔎 System Raw Data Integrity Log (Audit Check)"):
    st.write("Previewing live system logs feeding active workspace rendering structures:")
    st.dataframe(filtered_sales.head(50), use_container_width=True)
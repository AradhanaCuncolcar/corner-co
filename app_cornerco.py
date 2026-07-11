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

# Professional CSS injection for a clean corporate look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-sizing: border-box;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)
# ==============================================================================
# 2. DATA LOADING & ROBUST CLEANING
# ==============================================================================
@st.cache_data
def load_and_prepare_data():
    # Load raw datasets
    sales = pd.read_csv("cornerco_sales (1).csv")
    enquiries = pd.read_csv("cornerco_enquiries.csv")
    
    # Clean Sales Data: enforce standard dates and lowercase text formatting
    sales['date'] = pd.to_datetime(sales['date'])
    sales['item_name'] = sales['item_name'].astype(str).str.lower().str.strip()
    sales['total_revenue'] = sales['quantity'] * sales['unit_price']
    
    # Clean Enquiries Data
    enquiries['date'] = pd.to_datetime(enquiries['date'])
    
    # Correct Aggregation Phase: Roll transactions up to a safe, daily level first
    daily_sales = sales.groupby('date').agg(
        daily_revenue=('total_revenue', 'sum'),
        daily_transactions=('receipt_id', 'nunique')
    ).reset_index()
    
    # Aligned Merging Strategy: Perform a Left Merge as done in your notebook framework
    # This anchors the daily metrics specifically to active sales operational dates
    merged_daily = pd.merge(daily_sales, enquiries, on='date', how='left').fillna(0)
    
    return sales, enquiries, merged_daily

try:
    df_sales, df_enquiries, df_merged = load_and_prepare_data()
except Exception as e:
    st.error(f"❌ Error loading data files. Please check file paths. Details: {e}")
    st.stop()
    
# ==============================================================================
# 3. GLOBAL FILTER SIDEBAR
# ==============================================================================
st.sidebar.title("📊 Strategic Controls")
st.sidebar.markdown("Filter the business view globally.")

# Date Range Filter
min_date = df_sales['date'].min().to_pydatetime()
max_date = df_sales['date'].max().to_pydatetime()
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Convert dates back to datetime64 for matching
start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)

# Demographic & Segment Filters
all_ages = sorted(df_sales['customer_age_group'].dropna().unique())
selected_ages = st.sidebar.multiselect("Customer Age Groups", options=all_ages, default=all_ages)

max_dist = float(df_sales['customer_distance_km'].max())
selected_distance = st.sidebar.slider("Customer Distance Radius (km)", 0.0, max_dist, (0.0, max_dist))

# Apply Global Filters to Datasets
filtered_sales = df_sales[
    (df_sales['date'] >= start_dt) & (df_sales['date'] <= end_dt) &
    (df_sales['customer_age_group'].isin(selected_ages)) &
    (df_sales['customer_distance_km'].between(selected_distance[0], selected_distance[1]))
]

filtered_daily = df_merged[
    (df_merged['date'] >= start_dt) & (df_merged['date'] <= end_dt)
]

# ==============================================================================
# 4. DASHBOARD HEADER & EXECUTIVE RECOMMENDATION
# ==============================================================================
st.title("💼 Corner&Co. — Omnichannel Investment Strategy")
st.markdown("### Evaluating Unmet Digital Demand Beyond the Cash Register")
st.write("This interactive console contrasts structural brick-and-mortar sales with daily "
         "customer demand inquiries logged directly from the till point.")

# Highly professional executive summary box
st.info(
    "💡 **Consultant Recommendation:** **INVEST NOW.** While current online transactions sit near 0% "
    "due to an infrastructure block, out-of-store delivery requests and online order attempts represent a substantial "
    "untapped market, particularly among high-value digital-ready cohorts traveling long distances."
)
st.markdown("---")

# ==============================================================================
# 5. HIGH-LEVEL EXECUTIVE METRIC CARDS
# ==============================================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_rev = filtered_sales['total_revenue'].sum()
    st.metric(label="Total Revenue Captured", value=f"${total_rev:,.2f}")

with col2:
    total_delivery_req = filtered_daily['delivery_requests'].sum()
    st.metric(label="Explicit Delivery Requests", value=f"{int(total_delivery_req):,}")

with col3:
    total_online_attempts = filtered_daily['online_orders_attempted'].sum()
    st.metric(label="Blocked Online Order Attempts", value=f"{int(total_online_attempts):,}")

with col4:
    total_walkouts = filtered_daily['customers_turned_away_peak'].sum()
    st.metric(label="Peak Friction Walkouts", value=f"{int(total_walkouts):,}", delta="Lost Potential Rev", delta_color="inverse")

st.markdown("---")

# ==============================================================================
# 6. CORE ANALYTICAL VISUALIZATIONS
# ==============================================================================
tab1, tab2, tab3 = st.tabs(["📈 Unmet Demand & Operations", "👥 Customer Profiling", "📦 Inventory Performance"])

# TAB 1: OPERATIONAL FRICTION AND DEMAND SIGNALS
with tab1:
    st.subheader("The Demand vs. Infrastructure Gap")
    
    # Chart 1: Daily Trend of Missed Opportunities
    fig_demand = go.Figure()
    fig_demand.add_trace(go.Scatter(x=filtered_daily['date'], y=filtered_daily['delivery_requests'],
                                    mode='lines', name='Delivery Requests', line=dict(color='#1f77b4', width=2)))
    fig_demand.add_trace(go.Scatter(x=filtered_daily['date'], y=filtered_daily['online_orders_attempted'],
                                    mode='lines', name='Attempted Web Orders', line=dict(color='#ff7f0e', width=2)))
    fig_demand.update_layout(
        title="Daily Unmet Digital Demand Trends",
        xaxis_title="Timeline",
        yaxis_title="Count of Customer Signals",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        template="plotly_white"
    )
    st.plotly_chart(fig_demand, use_container_width=True)
    
    # Chart 2: Congestion & Peak Hours
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
        st.caption("Operational Bottleneck: High volumes create checkout queues, inducing the walkouts displayed on the right.")
        
    with c2:
        fig_walk = px.box(filtered_daily, y='customers_turned_away_peak', 
                          title="Daily Customer Loss Distribution During Peaks",
                          labels={'customers_turned_away_peak': 'Customers Left Due to Queues'},
                          color_discrete_sequence=['#d62728'])
        fig_walk.update_layout(template="plotly_white")
        st.plotly_chart(fig_walk, use_container_width=True)
        st.caption("Proof of Concept for Order-Ahead: Digital ordering reduces pickup queues and saves these walkout sales.")

# TAB 2: DEMOGRAPHIC & LOGISTICAL SEGMENTATION
with tab2:
    st.subheader("Target Audience Readiness Profile")
    c3, c4 = st.columns(2)
    
    with c3:
        # Age Profile Breakdown
        age_mix = filtered_sales.groupby('customer_age_group')['receipt_id'].nunique().reset_index()
        fig_age = px.pie(age_mix, values='receipt_id', names='customer_age_group', 
                         title="Customer Base Age Group Allocation",
                         hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_age.update_layout(legend=dict(orientation="h"))
        st.plotly_chart(fig_age, use_container_width=True)
        st.caption("E-Commerce Adoption Readiness: Younger bands dominate foot traffic, validating high app compatibility.")
        
    with c4:
        # Distance Logistics Distribution
        fig_dist = px.histogram(filtered_sales, x='customer_distance_km', nbins=20,
                                title="Customer Traveling Distance Distribution",
                                labels={'customer_distance_km': 'Distance to Store (km)'},
                                color_discrete_sequence=['#9467bd'])
        fig_dist.update_layout(template="plotly_white", yaxis_title="Transaction Frequency")
        st.plotly_chart(fig_dist, use_container_width=True)
        st.caption("Logistics Rationale: Substantial transaction clusters beyond 3km justify immediate home-delivery expansion.")

# TAB 3: CLEANED PRODUCT PERFORMANCE
with tab3:
    st.subheader("Product Catalogue Analytics")
    
    # Local UI Control to switch ranking metric
    rank_metric = st.radio("Rank Inventory By:", options=["Units Sold Volume", "Revenue Generated"], horizontal=True)
    
    # Aggregate clean data
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
    st.caption("Inventory Strategy: These core items should be prioritized as front-page promotional tiles on the new web app.")

# ==============================================================================
# 7. FOOTER DATA AUDIT LOG
# ==============================================================================
st.markdown("---")
with st.expander("🔎 System Raw Data Integrity Log (Audit Check)"):
    st.write("Below is a preview of the clean, merged dataset running underneath your active filter selection:")
    st.dataframe(filtered_sales.head(50), use_container_width=True)

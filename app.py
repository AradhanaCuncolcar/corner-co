import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# 1. PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Corner&Co. Strategic Analytics",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #F3EEE1; }
    .metric-card {
        background-color: #FBF8F0;
        padding: 18px;
        border-radius: 8px;
        border: 1px solid #C9BE9C;
    }
    div[data-testid="stMetric"] {
        background-color: #FBF8F0;
        border: 1px solid #C9BE9C;
        border-radius: 8px;
        padding: 14px 16px;
    }
    .rec-card {
        background-color: #FBF8F0;
        border: 1px solid #C9BE9C;
        border-left: 5px solid #C97A2B;
        border-radius: 3px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .rec-card h4 { margin-bottom: 4px; color: #1D3620; }
    .rec-card .impact { font-family: monospace; font-size: 12.5px; color: #2F5233; font-weight: 600; margin-top: 8px; }
    .banner-box {
        background: linear-gradient(135deg, #2F5233 0%, #1D3620 100%);
        color: #F3EEE1; border-radius: 8px; padding: 20px 22px; margin-bottom: 10px;
    }
    .banner-box b { color: #fff; }
    </style>
    """, unsafe_allow_html=True)

CATEGORY_ORDER = ['18-25', '26-35', '36-50', '51-65', '65+']
PALETTE = ['#2F5233', '#C97A2B', '#5C7A57', '#A8402F', '#8a9e73', '#e0c07a', '#4A5A46', '#b7896a']

# One-time "go online" setup-cost model, by category handling complexity.
# These are planning-level estimates, not vendor quotes — see the notes in the
# Investment & Payback tab for the assumptions behind each number.
CATEGORY_MODEL = {
    'Fresh':     {'base_cost': 180, 'per_unit': 3.0, 'weeks': 6},
    'Dairy':     {'base_cost': 150, 'per_unit': 2.5, 'weeks': 5},
    'Frozen':    {'base_cost': 180, 'per_unit': 3.0, 'weeks': 6},
    'Bakery':    {'base_cost': 90,  'per_unit': 1.5, 'weeks': 3},
    'Pantry':    {'base_cost': 50,  'per_unit': 1.0, 'weeks': 2},
    'Household': {'base_cost': 50,  'per_unit': 1.0, 'weeks': 2},
    'Beverages': {'base_cost': 50,  'per_unit': 1.0, 'weeks': 2},
    'Snacks':    {'base_cost': 50,  'per_unit': 1.0, 'weeks': 2},
    'Other':     {'base_cost': 50,  'per_unit': 1.0, 'weeks': 2},
}


def category_model(cat):
    return CATEGORY_MODEL.get(cat, CATEGORY_MODEL['Other'])


# ==============================================================================
# 2. DATA LOADING & CLEANING
# ==============================================================================
@st.cache_data
def load_and_prepare_data():
    sales = pd.read_csv("cornerco_sales.csv")
    enquiries = pd.read_csv("cornerco_enquiries.csv")

    sales.columns = sales.columns.str.strip()
    enquiries.columns = enquiries.columns.str.strip()

    # Clean item names & drop junk/test rows that don't represent real products
    sales['item_name'] = sales['item_name'].astype(str).str.lower().str.strip()
    junk = ['test', 'xxx', 'test item']
    sales = sales[~sales['item_name'].isin(junk)].copy()
    sales['item_display'] = sales['item_name'].str.title()

    sales['date'] = pd.to_datetime(sales['date'], format='%d-%m-%Y')
    sales = sales.dropna(subset=['unit_price']).copy()
    sales['total_revenue'] = sales['quantity'] * sales['unit_price']

    enquiries['date'] = pd.to_datetime(enquiries['date'], format='%d-%m-%Y')

    daily_sales = sales.groupby('date').agg(
        daily_revenue=('total_revenue', 'sum'),
        daily_transactions=('receipt_id', 'nunique')
    ).reset_index()

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
st.sidebar.title("🧾 Filter Console")
st.sidebar.markdown("Slice the whole dashboard — every chart below recalculates live.")

min_date = df_sales['date'].min().to_pydatetime()
max_date = df_sales['date'].max().to_pydatetime()
start_date, end_date = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
start_dt, end_dt = pd.to_datetime(start_date), pd.to_datetime(end_date)

all_ages = [a for a in CATEGORY_ORDER if a in df_sales['customer_age_group'].unique()]
selected_ages = st.sidebar.multiselect("Customer Age Groups", options=all_ages, default=all_ages)

all_categories = sorted(df_sales['category'].dropna().unique())
selected_categories = st.sidebar.multiselect("Product Categories", options=all_categories, default=all_categories)

max_dist = float(df_sales['customer_distance_km'].max())
min_dist = float(df_sales['customer_distance_km'].min())
selected_distance = st.sidebar.slider("Customer Distance Radius (km)", min_dist, max_dist, (min_dist, max_dist))

loyalty_choice = st.sidebar.radio("Loyalty Status", options=["All", "Member", "Non-member"], horizontal=True)

st.sidebar.markdown("---")
capture_rate = st.sidebar.slider(
    "🧮 Target Online Capture Rate",
    min_value=5, max_value=50, value=20, step=1,
    help="Used in the Investment & Payback tab: the share of a product's total demand "
         "assumed to shift online once launched, for products with little or no online history yet."
) / 100.0

# Apply filters
filtered_sales = df_sales[
    (df_sales['date'] >= start_dt) & (df_sales['date'] <= end_dt) &
    (df_sales['customer_age_group'].isin(selected_ages)) &
    (df_sales['category'].isin(selected_categories)) &
    (df_sales['customer_distance_km'].between(selected_distance[0], selected_distance[1]))
].copy()

if loyalty_choice == "Member":
    filtered_sales = filtered_sales[filtered_sales['loyalty_member'] == 'Yes']
elif loyalty_choice == "Non-member":
    filtered_sales = filtered_sales[filtered_sales['loyalty_member'] == 'No']

filtered_enq = df_enquiries[(df_enquiries['date'] >= start_dt) & (df_enquiries['date'] <= end_dt)].copy()

online_sales = filtered_sales[filtered_sales['channel'] == 'Online']
instore_sales = filtered_sales[filtered_sales['channel'] == 'In-store']

st.sidebar.markdown("---")
st.sidebar.caption(f"**{len(filtered_sales):,}** transaction lines matched")

# ==============================================================================
# 4. DASHBOARD HEADER
# ==============================================================================
st.title("💼 Corner&Co. — Omnichannel Investment Strategy")
st.markdown("### The till says a few percent online. The street says otherwise.")

st.markdown(
    """
    <div class="banner-box">
    💡 <b>Reading the room:</b> Online channel share looks small in the top-line numbers —
    but distance-driven demand doesn't disappear when the checkout is slow, it just goes to a
    competitor's delivery van instead. This dashboard quantifies the gap and where to close it first.
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# ==============================================================================
# 5. HIGH-LEVEL KPI METRICS
# ==============================================================================
total_rev = filtered_sales['total_revenue'].sum()
online_rev = online_sales['total_revenue'].sum()
online_pct = (online_rev / total_rev * 100) if total_rev else 0
online_receipts = online_sales['receipt_id'].nunique()
instore_receipts = instore_sales['receipt_id'].nunique()
aov_online = (online_rev / online_receipts) if online_receipts else 0
aov_instore = (instore_sales['total_revenue'].sum() / instore_receipts) if instore_receipts else 0

delivery_requests = int(filtered_enq['delivery_requests'].sum())
attempted_orders = int(filtered_enq['online_orders_attempted'].sum())
turned_away = int(filtered_enq['customers_turned_away_peak'].sum())
competitor_days = int(filtered_enq['competitor_delivery_nearby'].sum())
total_days = len(filtered_enq)

gap_orders = max(attempted_orders - online_receipts, 0)
potential_checkout_fix = gap_orders * aov_online
potential_delivery = delivery_requests * aov_online

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Revenue", f"${total_rev:,.0f}")
col2.metric("Online Revenue", f"${online_rev:,.0f}", f"{online_pct:.1f}% of total")
col3.metric("Delivery Requests", f"{delivery_requests:,}")
col4.metric("Blocked Web Orders", f"{attempted_orders:,}")
col5.metric("Peak Walkouts", f"{turned_away:,}")
col6.metric("Recovery Opportunity", f"${potential_checkout_fix + potential_delivery:,.0f}")

st.markdown("---")

# ==============================================================================
# 6. CORE ANALYTICAL TABS
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📍 Opportunity", "🏷️ Pricing", "📦 Products", "📈 Demand Gap",
    "👥 Segments", "🚦 Friction", "🧮 Investment & Payback"
])

# ---- TAB 1: OPPORTUNITY (distance vs online adoption) ----
with tab1:
    st.subheader("Online Adoption Rises Sharply With Distance")
    bins = [0, 1, 2, 3, 5, np.inf]
    labels = ['0-1km', '1-2km', '2-3km', '3-5km', '5km+']
    fs = filtered_sales.copy()
    fs['dist_band'] = pd.cut(fs['customer_distance_km'], bins=bins, labels=labels)
    band_stats = fs.groupby('dist_band', observed=True).apply(
        lambda g: pd.Series({
            'online_pct': (g['channel'] == 'Online').mean() * 100 if len(g) else 0,
            'n': len(g)
        })
    ).reset_index()

    if band_stats.empty or band_stats['n'].sum() == 0:
        st.info("No transactions match the current filters.")
    else:
        colors = ['#C97A2B' if i == len(band_stats) - 1 else '#2F5233' for i in range(len(band_stats))]
        fig = go.Figure(go.Bar(x=band_stats['dist_band'], y=band_stats['online_pct'],
                                marker_color=colors, text=band_stats['online_pct'].round(1).astype(str) + '%',
                                textposition='outside'))
        fig.update_layout(template="plotly_white", yaxis_title="Online share of transactions (%)",
                           xaxis_title="Distance from store", yaxis_range=[0, 100])
        st.plotly_chart(fig, width="stretch")

        far_pct = band_stats.iloc[-1]['online_pct']
        near_pct = band_stats.iloc[0]['online_pct']
        st.markdown(
            f"""
            <div class="banner-box">
            <b>{far_pct:.0f}%</b> of customers in the farthest distance band already order online,
            vs. <b>{near_pct:.0f}%</b> for those closest to the till — distance is the strongest single
            predictor of digital intent in this data.
            </div>
            """,
            unsafe_allow_html=True
        )

# ---- TAB 2: PRICING PARITY ----
with tab2:
    st.subheader("Price Comparison — Online vs In-Store")
    st.caption("Products sold on both channels, compared directly. A price gap this small suggests pricing isn't the barrier holding digital back.")

    piv = filtered_sales.pivot_table(index='item_display', columns='channel', values='unit_price', aggfunc='mean')
    piv = piv.dropna(subset=[c for c in ['In-store', 'Online'] if c in piv.columns])
    if 'In-store' in piv.columns and 'Online' in piv.columns and not piv.empty:
        piv = piv.join(filtered_sales.groupby('item_display')['category'].first())
        piv['match'] = np.isclose(piv['In-store'], piv['Online'], atol=0.01)
        piv = piv.reset_index().sort_values('item_display')
        piv_display = piv.rename(columns={'item_display': 'Product', 'category': 'Category'})
        piv_display['In-store'] = piv_display['In-store'].map('${:.2f}'.format)
        piv_display['Online'] = piv_display['Online'].map('${:.2f}'.format)
        piv_display['Status'] = piv_display['match'].map({True: '✓ identical', False: '⚠ differs'})
        st.dataframe(piv_display[['Product', 'Category', 'In-store', 'Online', 'Status']],
                     width="stretch", hide_index=True)
    else:
        st.info("No products currently sold on both channels in this filter.")

    c1, c2 = st.columns(2)
    with c1:
        fig_aov = go.Figure(go.Bar(x=['In-Store', 'Online'], y=[aov_instore, aov_online],
                                    marker_color=['#2F5233', '#C97A2B']))
        fig_aov.update_layout(template="plotly_white", title="Average Order Value", yaxis_title="$ per line item")
        st.plotly_chart(fig_aov, width="stretch")
    with c2:
        st.metric("Online AOV", f"${aov_online:.2f}")
        st.metric("In-Store AOV", f"${aov_instore:.2f}")
        st.caption("Close average order values across channels reinforce that price isn't the digital blocker — capacity and checkout infrastructure are.")

# ---- TAB 3: PRODUCTS ----
with tab3:
    st.subheader("What Customers Buy When They Go Digital")
    c1, c2 = st.columns(2)
    with c1:
        top_online = online_sales.groupby('item_display')['total_revenue'].sum().sort_values(ascending=False).head(10).reset_index()
        if top_online.empty:
            st.info("No online transactions in this filter.")
        else:
            fig = px.bar(top_online, x='total_revenue', y='item_display', orientation='h',
                         title="Top Products — Online Revenue",
                         labels={'total_revenue': 'Online Revenue ($)', 'item_display': ''},
                         color='total_revenue', color_continuous_scale='Greens')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, template="plotly_white", coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")
    with c2:
        cat_online = online_sales.groupby('category')['total_revenue'].sum().sort_values(ascending=False).reset_index()
        if cat_online.empty:
            st.info("No online transactions in this filter.")
        else:
            fig = px.pie(cat_online, values='total_revenue', names='category', hole=0.5,
                         title="Online Spend by Category", color_discrete_sequence=PALETTE)
            st.plotly_chart(fig, width="stretch")

# ---- TAB 4: DEMAND VS INFRASTRUCTURE GAP ----
with tab4:
    st.subheader("Demand vs. Infrastructure — The Growing Gap")
    fs = filtered_sales.copy()
    fs['month'] = fs['date'].dt.to_period('M').astype(str)
    fe = filtered_enq.copy()
    fe['month'] = fe['date'].dt.to_period('M').astype(str)

    months = sorted(fe['month'].unique())
    delivery_by_month = fe.groupby('month')['delivery_requests'].sum().reindex(months, fill_value=0)
    attempted_by_month = fe.groupby('month')['online_orders_attempted'].sum().reindex(months, fill_value=0)
    online_rev_by_month = fs[fs['channel'] == 'Online'].groupby('month')['total_revenue'].sum().reindex(months, fill_value=0)

    if len(months) == 0:
        st.info("No data in this filter.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=months, y=delivery_by_month, name='Delivery Requests', marker_color='#5C7A57'))
        fig.add_trace(go.Bar(x=months, y=attempted_by_month, name='Attempted Web Orders', marker_color='#E8B87A'))
        fig.add_trace(go.Scatter(x=months, y=online_rev_by_month, name='Fulfilled Online Revenue ($)',
                                  yaxis='y2', mode='lines+markers', line=dict(color='#A8402F', width=3)))
        fig.update_layout(
            template="plotly_white", barmode='group',
            yaxis=dict(title='Count of signals'),
            yaxis2=dict(title='Online revenue ($)', overlaying='y', side='right'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02)
        )
        st.plotly_chart(fig, width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("Unconverted Web Order Attempts", f"{gap_orders:,}")
    c2.metric("Recoverable via Checkout Fix", f"${potential_checkout_fix:,.0f}")
    c3.metric("Upside from Delivery Requests", f"${potential_delivery:,.0f}")

# ---- TAB 5: SEGMENTS ----
with tab5:
    st.subheader("Who's Ready to Go Digital First")
    c1, c2, c3 = st.columns(3)

    with c1:
        age_stats = filtered_sales.groupby('customer_age_group').apply(
            lambda g: (g['channel'] == 'Online').mean() * 100, include_groups=False
        ).reindex([a for a in CATEGORY_ORDER if a in selected_ages]).dropna().reset_index()
        age_stats.columns = ['age_group', 'online_pct']
        if age_stats.empty:
            st.info("No data.")
        else:
            fig = px.bar(age_stats, x='age_group', y='online_pct', title="By Age Group",
                         labels={'online_pct': 'Online share (%)', 'age_group': ''},
                         color_discrete_sequence=['#2F5233'])
            fig.update_layout(template="plotly_white", yaxis_range=[0, 100])
            st.plotly_chart(fig, width="stretch")

    with c2:
        fs2 = filtered_sales.copy()
        fs2['dist_band'] = pd.cut(fs2['customer_distance_km'], bins=[0, 1, 2, 3, 5, np.inf],
                                   labels=['0-1km', '1-2km', '2-3km', '3-5km', '5km+'])
        dist_stats = fs2.groupby('dist_band', observed=True).apply(
            lambda g: (g['channel'] == 'Online').mean() * 100, include_groups=False
        ).reset_index()
        dist_stats.columns = ['dist_band', 'online_pct']
        if dist_stats.empty:
            st.info("No data.")
        else:
            fig = px.bar(dist_stats, x='dist_band', y='online_pct', title="By Distance Band",
                         labels={'online_pct': 'Online share (%)', 'dist_band': ''},
                         color_discrete_sequence=['#C97A2B'])
            fig.update_layout(template="plotly_white", yaxis_range=[0, 100])
            st.plotly_chart(fig, width="stretch")

    with c3:
        loy_stats = filtered_sales.groupby('loyalty_member').apply(
            lambda g: (g['channel'] == 'Online').mean() * 100, include_groups=False
        ).reset_index()
        loy_stats.columns = ['loyalty', 'online_pct']
        loy_stats['loyalty'] = loy_stats['loyalty'].map({'Yes': 'Member', 'No': 'Non-member'})
        if loy_stats.empty:
            st.info("No data.")
        else:
            fig = px.bar(loy_stats, x='loyalty', y='online_pct', title="By Loyalty Status",
                         labels={'online_pct': 'Online share (%)', 'loyalty': ''},
                         color_discrete_sequence=['#5C7A57'])
            fig.update_layout(template="plotly_white", yaxis_range=[0, 100])
            st.plotly_chart(fig, width="stretch")

# ---- TAB 6: OPERATIONAL FRICTION ----
with tab6:
    st.subheader("Operational Friction at the Till")
    c1, c2 = st.columns(2)
    with c1:
        hourly_tx = filtered_sales.groupby('hour')['receipt_id'].nunique().reset_index()
        if hourly_tx.empty:
            st.info("No data.")
        else:
            fig = px.bar(hourly_tx, x='hour', y='receipt_id', title="Transaction Volume by Hour",
                         labels={'hour': 'Hour (24h)', 'receipt_id': 'Transactions'},
                         color_discrete_sequence=['#2F5233'])
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, width="stretch")
    with c2:
        if total_days == 0:
            st.info("No data.")
        else:
            fig = go.Figure(go.Pie(
                labels=['Competitor delivery active nearby', 'No competitor delivery'],
                values=[competitor_days, max(total_days - competitor_days, 0)],
                hole=0.6, marker_colors=['#A8402F', '#C9BE9C']
            ))
            fig.update_layout(template="plotly_white", title="Competitive Pressure Nearby")
            st.plotly_chart(fig, width="stretch")
        st.caption(f"A competitor delivery option was active nearby on **{competitor_days} of {total_days}** days in the filtered range.")

# ---- TAB 7: INVESTMENT & PAYBACK ----
with tab7:
    st.subheader("Product-by-Product: What It Costs to Go Online")
    st.markdown(
        """
        <div class="banner-box">
        🧮 <b>How this is modeled:</b> Corner&amp;Co.'s ledger records sales, not vendor quotes — so setup
        cost and launch time are <b>planning estimates</b>, not invoiced figures. Each product gets a
        one-time setup cost from its category's handling complexity (cold-chain items like Fresh, Dairy &amp;
        Frozen cost more and take longer than shelf-stable Pantry or Household goods), plus a small variable
        cost tied to sales volume. Payback period compares that cost against projected monthly online revenue —
        either the product's <i>actual</i> online run rate today, or the target capture rate (set in the sidebar)
        applied to its total sales, whichever is higher.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption(f"Current target online capture rate: **{capture_rate*100:.0f}%** — adjust it from the sidebar.")

    months_in_range = max((end_dt - start_dt).days / 30.44, 1 / 30.44)

    if filtered_sales.empty:
        st.info("No products in this filter.")
    else:
        grouped = filtered_sales.groupby(['item_display', 'category']).agg(
            total_rev=('total_revenue', 'sum'),
            total_qty=('quantity', 'sum'),
            online_rev=('total_revenue', lambda s: s[filtered_sales.loc[s.index, 'channel'] == 'Online'].sum())
        ).reset_index()

        rows = []
        for _, r in grouped.iterrows():
            model = category_model(r['category'])
            avg_monthly_qty = r['total_qty'] / months_in_range
            avg_monthly_rev = r['total_rev'] / months_in_range
            online_monthly_rev = r['online_rev'] / months_in_range
            setup_cost = model['base_cost'] + model['per_unit'] * avg_monthly_qty
            projected_monthly = max(online_monthly_rev, avg_monthly_rev * capture_rate)
            payback_months = setup_cost / projected_monthly if projected_monthly > 0 else np.inf
            rows.append({
                'Product': r['item_display'], 'Category': r['category'],
                'Spend': r['total_rev'], 'Setup Cost': setup_cost,
                'Launch (weeks)': model['weeks'], 'Payback (months)': payback_months,
                'Projected Monthly Online Rev': projected_monthly
            })

        invest_df = pd.DataFrame(rows).sort_values('Payback (months)')

        total_investment = invest_df['Setup Cost'].sum()
        finite = invest_df[np.isfinite(invest_df['Payback (months)'])]
        blended_payback = (
            (finite['Payback (months)'] * finite['Setup Cost']).sum() / finite['Setup Cost'].sum()
            if not finite.empty else np.nan
        )
        quick_wins = int((invest_df['Payback (months)'] <= 3).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Setup Investment", f"${total_investment:,.0f}")
        c2.metric("Blended Payback Period", f"{blended_payback:.1f} mo" if not np.isnan(blended_payback) else "—")
        c3.metric("Quick Wins (≤3 mo payback)", quick_wins)

        plot_df = invest_df.copy()
        plot_df['Payback (capped)'] = plot_df['Payback (months)'].clip(upper=24)
        fig = px.scatter(
            plot_df, x='Setup Cost', y='Payback (capped)', size='Spend', color='Category',
            hover_name='Product', color_discrete_sequence=PALETTE,
            labels={'Payback (capped)': 'Payback period (months, capped at 24)', 'Setup Cost': 'Setup cost ($)'},
            title="Investment vs. Payback, by Product"
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, width="stretch")

        display_df = invest_df.copy()
        display_df['Spend'] = display_df['Spend'].map('${:,.2f}'.format)
        display_df['Setup Cost'] = display_df['Setup Cost'].map('${:,.2f}'.format)
        display_df['Launch (weeks)'] = display_df['Launch (weeks)'].astype(str) + ' wk'
        display_df['Payback (months)'] = display_df['Payback (months)'].apply(
            lambda v: f"{v:.1f} mo" if np.isfinite(v) else "N/A"
        )
        st.dataframe(
            display_df[['Product', 'Category', 'Spend', 'Setup Cost', 'Launch (weeks)', 'Payback (months)']],
            width="stretch", hide_index=True
        )

st.markdown("---")

# ==============================================================================
# 7. RECOMMENDED NEXT MOVES (six moves)
# ==============================================================================
st.header("🎯 Recommended Next Moves")
st.caption("Six moves, ordered by how directly they close the gaps shown above.")

recs = [
    ("MOVE 01 · INFRASTRUCTURE", "Fix the online checkout first",
     "Web-order attempts consistently outnumber completed online sales. Remove that friction before spending on acquisition.",
     "Zero-new-demand recovery — see the Demand Gap tab, recalculated live"),
    ("MOVE 02 · DELIVERY ROLLOUT", "Launch delivery for the far distance ring first",
     "Adoption is consistently highest for customers furthest from the store. Pilot delivery zones outward, prioritising proven appetite.",
     "Filter to any date range — the distance pattern holds"),
    ("MOVE 03 · CATALOGUE", "Lead with the top online categories",
     "Use the category donut in the Products tab to pick the categories driving online revenue this month, not a guess at the full range.",
     "Updates automatically as you filter"),
    ("MOVE 04 · MARKETING", "Target the highest-adopting age segment",
     "Use the Segments tab to identify which cohort to target first — isolate it with the age filter to check basket size and category mix.",
     "Filterable segment-by-segment"),
    ("MOVE 05 · PEAK HOURS", "Use online ordering as a peak-hour release valve",
     "Cross-reference the hourly chart in the Friction tab with walkout volume to time a 'skip the queue' push.",
     "Live hourly breakdown in the Friction tab"),
    ("MOVE 06 · COMPETITIVE DEFENSE", "Treat delivery as retention, not just growth",
     "Track the competitor-pressure donut across different date windows to see if the threat is growing.",
     f"Active on {competitor_days} of {total_days} days in the current filter"),
]

rec_cols = st.columns(2)
for i, (tag, title, body, impact) in enumerate(recs):
    with rec_cols[i % 2]:
        st.markdown(
            f"""
            <div class="rec-card">
                <div style="font-family:monospace; font-size:11px; color:#C97A2B; letter-spacing:.08em;">{tag}</div>
                <h4>{title}</h4>
                <p style="color:#4A5A46; font-size:13.5px;">{body}</p>
                <div class="impact">{impact}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==============================================================================
# 8. DATA AUDIT PREVIEW LOG
# ==============================================================================
st.markdown("---")
with st.expander("🔎 System Raw Data Integrity Log (Audit Check)"):
    st.write("Previewing filtered ledger transactions directly feeding the dashboard:")
    st.dataframe(filtered_sales.head(50), width="stretch")

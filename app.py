import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine

st.set_page_config(page_title="Cart2Insights Dashboard", layout="wide")
st.title("🛒 Cart2Insights: E-Commerce Analytics Dashboard")

# 1. Database Connection Cache
@st.cache_resource
def get_db_connection():
    db_path = 'D:/Bharathi/python code/cleaned_data/cart2insights.db'
    return create_engine(f'sqlite:///{db_path}')

engine = get_db_connection()

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Overview", 
    "Sales & Trends", 
    "Delivery Analytics", 
    "Customer Satisfaction", 
    "Hypothesis Testing"
])

# ----------------- TAB 1: EXECUTIVE OVERVIEW -----------------
with tab1:
    st.subheader("High-Level Business KPIs")
    kpi_query = """
    SELECT 
        (SELECT ROUND(SUM(payment_value), 2) FROM order_payments) AS total_revenue,
        (SELECT COUNT(order_id) FROM orders) AS total_orders,
        (SELECT COUNT(DISTINCT customer_unique_id) FROM customers) AS total_customers,
        (SELECT COUNT(DISTINCT seller_id) FROM sellers) AS total_sellers,
        (SELECT ROUND(AVG(review_score), 2) FROM order_reviews) AS avg_review_score;
    """
    kpis = pd.read_sql(kpi_query, con=engine).iloc[0]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Revenue", f"R$ {kpis['total_revenue']:,.2f}")
    col2.metric("Total Orders", f"{int(kpis['total_orders']):,}")
    col3.metric("Total Customers", f"{int(kpis['total_customers']):,}")
    col4.metric("Total Sellers", f"{int(kpis['total_sellers']):,}")
    col5.metric("Avg Review Rating", f"{kpis['avg_review_score']} / 5.0")

# ----------------- TAB 2: SALES & TRENDS -----------------
with tab2:
    st.subheader("Monthly Revenue Growth")
    trend_query = """
    SELECT 
        strftime('%Y-%m', o.order_purchase_timestamp) AS order_month,
        ROUND(SUM(p.payment_value), 2) AS monthly_revenue
    FROM orders o
    JOIN order_payments p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY order_month
    ORDER BY order_month;
    """
    df_trend = pd.read_sql(trend_query, con=engine)
    df_trend = df_trend[(df_trend['order_month'] >= '2017-01') & (df_trend['order_month'] <= '2018-08')]
    
    fig1, ax1 = plt.subplots(figsize=(10, 3.5))
    sns.lineplot(data=df_trend, x='order_month', y='monthly_revenue', marker='o', ax=ax1, color='#1f77b4')
    plt.xticks(rotation=45)
    plt.ylabel("Revenue (R$)")
    plt.xlabel("Month")
    st.pyplot(fig1)

    st.subheader("Top 10 Product Categories by Revenue")
    cat_query = """
    SELECT 
        pr.product_category_name_english AS category,
        ROUND(SUM(oi.price), 2) AS category_revenue
    FROM order_items oi
    JOIN products pr ON oi.product_id = pr.product_id
    GROUP BY category
    ORDER BY category_revenue DESC
    LIMIT 10;
    """
    df_cat = pd.read_sql(cat_query, con=engine)
    fig2, ax2 = plt.subplots(figsize=(9, 4))
    sns.barplot(data=df_cat, x='category_revenue', y='category', palette='Blues_r', ax=ax2)
    plt.xlabel("Revenue (R$)")
    st.pyplot(fig2)

# ----------------- TAB 3: DELIVERY ANALYTICS -----------------
with tab3:
    st.subheader("Operational Delivery Performance")
    deliv_query = """
    SELECT 
        julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp) AS delivery_time_days,
        julianday(order_delivered_customer_date) - julianday(order_estimated_delivery_date) AS delay_days
    FROM orders
    WHERE order_status = 'delivered' 
      AND order_delivered_customer_date IS NOT NULL
      AND delivery_time_days >= 0;
    """
    df_deliv = pd.read_sql(deliv_query, con=engine)
    df_deliv['delivery_status'] = np.where(df_deliv['delay_days'] > 0, 'Delayed', 'On-Time')
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**On-Time vs Delayed Delivery Split**")
        status_counts = df_deliv['delivery_status'].value_counts()
        fig3, ax3 = plt.subplots()
        ax3.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=['#2ca02c', '#d62728'], startangle=90)
        st.pyplot(fig3)
        
    with col_b:
        st.write("**Distribution of Actual Delivery Days**")
        fig4, ax4 = plt.subplots()
        sns.histplot(df_deliv['delivery_time_days'].clip(upper=40), bins=30, kde=True, ax=ax4, color='teal')
        plt.xlabel("Delivery Time (Days)")
        st.pyplot(fig4)

# ----------------- TAB 4: CUSTOMER SATISFACTION -----------------
with tab4:
    st.subheader("Customer Review Score Distribution")
    rev_query = "SELECT review_score, COUNT(review_id) AS count FROM order_reviews GROUP BY review_score;"
    df_rev = pd.read_sql(rev_query, con=engine)
    
    fig5, ax5 = plt.subplots(figsize=(7, 3))
    sns.barplot(data=df_rev, x='review_score', y='count', palette='viridis', ax=ax5)
    plt.xlabel("Review Rating (Stars)")
    plt.ylabel("Review Volume")
    st.pyplot(fig5)

# ----------------- TAB 5: HYPOTHESIS TESTING -----------------
with tab5:
    st.subheader("Statistical Validation & Business Insights")
    st.markdown("""
    ### 1. Delivery Delays vs. Customer Satisfaction (Two-Sample T-Test)
    * **Results:** $t = -91.82$, $p < 0.001$ (Delayed Mean: **2.55** vs. On-Time Mean: **4.21**)
    * **Finding:** Delayed orders suffer a statistically significant 1.66-star drop in review score.
    * **Business Impact:** Delivery timeliness is the primary driver of customer dissatisfaction. Courier SLAs must be renegotiated to maintain retention.

    ### 2. Category vs. Spending (One-Way ANOVA)
    * **Results:** $F = 151.03$, $p = 1.40 \\times 10^{-128}$
    * **Finding:** Average order spend varies significantly across product categories.
    * **Business Impact:** High-ticket categories require targeted financing options (e.g., installments) to facilitate checkout conversion.

    ### 3. Payment Method vs. Order Status (Chi-Square Test)
    * **Results:** $\\chi^2 = 210.72$, $df = 21$, $p = 2.78 \\times 10^{-33}$
    * **Finding:** Order outcomes are significantly dependent on the payment method used.
    * **Business Impact:** Non-instant payment methods (e.g., bank slip/boleto) experience higher cancellation rates, requiring automated payment reminder workflows.
    """)
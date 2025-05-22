import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="📈 Dashboard Finanziaria Avanzata", layout="wide")

st.markdown("""
    <style>
        .metric-label { font-weight: bold; color: #333; }
        .stPlotlyChart { padding: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# Aggiunta logo e titolo personalizzato
col_logo, col_titolo = st.columns([1, 5])
with col_logo:
    st.image("logo.png", width=60)
with col_titolo:
    st.markdown("<h1 style='margin-bottom: 0;'>FinSight – Dashboard Finanziaria</h1><h5 style='color: gray;'>Analisi interattiva di aziende quotate</h5>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

aziende = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Tesla": "TSLA",
    "Amazon": "AMZN",
    "Google": "GOOGL",
    "Meta": "META",
    "Netflix": "NFLX",
    "NVIDIA": "NVDA",
    "JPMorgan": "JPM",
    "Coca-Cola": "KO",
}

scelte = st.sidebar.multiselect("Seleziona fino a 3 aziende:", options=list(aziende.keys()), max_selections=3)
anni = st.sidebar.selectbox("Intervallo di tempo storico:", ["1y", "2y", "5y"], index=0)

@st.cache_data
def estrai_valore(df, keys):
    for key in keys:
        for idx in df.index:
            if key.lower() in idx.lower():
                val = df.loc[idx][0]
                if pd.notna(val):
                    return float(val)
    return None

def calcola_indicatori(ticker, periodo):
    az = yf.Ticker(ticker)
    try:
        fin = az.financials
        bal = az.balance_sheet
        cash = az.cashflow
        info = az.info
        hist = az.history(period=periodo)
    except Exception as e:
        st.error(f"Errore nel recupero dei dati per {ticker}: {e}")
        return None

    utile = estrai_valore(fin, ["Net Income"])
    equity = estrai_valore(bal, ["Total Stockholder Equity", "Total Equity"])
    assets = estrai_valore(bal, ["Total Assets"])
    debt = estrai_valore(bal, ["Total Liabilities", "Total Liab"])
    curr_assets = estrai_valore(bal, ["Total Current Assets", "Current Assets"])
    curr_liab = estrai_valore(bal, ["Total Current Liabilities", "Current Liabilities"])
    price = info.get("currentPrice", None)
    eps = info.get("trailingEps", None)
    shares = info.get("sharesOutstanding", None)

    roe = utile / equity if utile and equity else None
    roa = utile / assets if utile and assets else None
    dte = debt / equity if debt and equity else None
    current_ratio = curr_assets / curr_liab if curr_assets and curr_liab else None
    pe = price / eps if price and eps else None
    mkt_cap = price * shares if price and shares else None

    return {
        "ROE": roe,
        "ROA": roa,
        "Debt/Equity": dte,
        "Current Ratio": current_ratio,
        "P/E Ratio": pe,
        "Market Cap": mkt_cap,
        "Ticker": ticker,
        "Prezzo": price,
        "Istorico": hist,
        "Info": info,
    }

def rendimento_cumulato(df_close):
    returns = df_close.pct_change().fillna(0)
    cum_returns = (1 + returns).cumprod() * 100
    return cum_returns

if scelte:
    dati = {nome: calcola_indicatori(aziende[nome], anni) for nome in scelte if calcola_indicatori(aziende[nome], anni)}

    st.subheader("📈 Andamento Prezzo delle Aziende Selezionate")
    fig_comb = go.Figure()
    for nome, d in dati.items():
        fig_comb.add_trace(go.Scatter(x=d['Istorico'].index, y=d['Istorico']['Close'], name=nome))
    fig_comb.update_layout(title="Prezzo Azioni Storico", xaxis_title="Data", yaxis_title="Prezzo ($)", height=400)
    st.plotly_chart(fig_comb, use_container_width=True)

    # confronto con rendimento cumulato base 100 ---
    benchmark = yf.Ticker("^GSPC").history(period=anni)
    prezzi_df = pd.DataFrame({nome: d['Istorico']['Close'] for nome, d in dati.items()}).dropna()
    benchmark_df = benchmark['Close'].dropna()

    df_tutti = prezzi_df.copy()
    df_tutti['S&P 500'] = benchmark_df

    cum_returns = rendimento_cumulato(df_tutti)

    fig_cum = go.Figure()
    for col in cum_returns.columns:
        fig_cum.add_trace(go.Scatter(x=cum_returns.index, y=cum_returns[col], name=col))
    fig_cum.update_layout(
        title="Rendimento Cumulato Normalizzato (Base 100)",
        xaxis_title="Data",
        yaxis_title="Indice Rendimento",
        height=450
    )
    st.subheader("📊 Confronto Rendimento Cumulato")
    st.plotly_chart(fig_cum, use_container_width=True)

    # tabs, metriche, ecc...
    tabs = st.tabs(list(dati.keys()))
    for i, nome in enumerate(dati.keys()):
        d = dati[nome]
        with tabs[i]:
            st.subheader(f"📌 {nome} ({d['Ticker']})")
            col1, col2, col3 = st.columns(3)
            col1.metric("ROE", f"{d['ROE']*100:.2f}%" if d['ROE'] else "N/D")
            col2.metric("Debt/Equity", f"{d['Debt/Equity']:.2f}" if d['Debt/Equity'] else "N/D")
            col3.metric("Current Ratio", f"{d['Current Ratio']:.2f}" if d['Current Ratio'] else "N/D")

            st.markdown(f"**Settore:** {d['Info'].get('sector', 'N/D')}")
            st.markdown(f"**Descrizione:** {d['Info'].get('longBusinessSummary', '')[:300]}...")

        # Additional indicators
        d['Dividend Yield'] = d['Info'].get("dividendYield", None)
        d['Price/Book'] = d['Info'].get("priceToBook", None)

    if len(dati) > 1:
        st.subheader("📊 Confronto Indicatori")
        confronto = pd.DataFrame({nome: {
            "ROE": dati[nome]['ROE'] or 0,
            "ROA": dati[nome]['ROA'] or 0,
            "Debt/Equity": dati[nome]['Debt/Equity'] or 0,
            "Current Ratio": dati[nome]['Current Ratio'] or 0,
            "P/E Ratio": dati[nome]['P/E Ratio'] or 0,
            "Market Cap": dati[nome]['Market Cap'] or 0,
            "Price/Book": dati[nome].get('Price/Book', 0) or 0
        } for nome in dati}).T

        st.dataframe(confronto.style.format("{:.2f}"))

        colori = {
            "ROE": "#1f77b4",
            "ROA": "#ff7f0e",
            "Debt/Equity": "#2ca02c",
            "Current Ratio": "#d62728",
            "P/E Ratio": "#9467bd",
            "Market Cap": "#8c564b",
            "Price/Book": "#bcbd22"
        }
        for metrica in confronto.columns:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=confronto.index,
                y=confronto[metrica],
                name=metrica,
                marker_color=colori.get(metrica, None)
            ))
            fig.update_layout(title=f"Confronto: {metrica}", xaxis_title="Azienda", yaxis_title=metrica, height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Analisi statistica
    st.subheader("📊 Analisi Statistica dei Log Returns")

    prezzi = {nome: d['Istorico']['Close'] for nome, d in dati.items()}
    prezzi_df = pd.DataFrame(prezzi).dropna()

    benchmark_df = benchmark['Close'].dropna()
    prezzi_df['S&P 500'] = benchmark_df
    prezzi_returns = np.log(prezzi_df / prezzi_df.shift(1)).dropna()

    st.markdown("### Statistiche descrittive (log returns)")
    stats = prezzi_returns.describe().T[['mean', 'std', 'min', 'max']]
    stats.rename(columns={
            'mean': 'Media',
            'std': 'Deviazione Std',
            'min': 'Min',
            'max': 'Max'
        }, inplace=True)
    st.dataframe(stats.style.format("{:.4f}"))

    st.markdown("### Correlazione tra gli asset (log returns)")
    correlazione = prezzi_returns.corr()
    st.dataframe(correlazione.style.background_gradient(cmap='coolwarm').format("{:.2f}"))

    st.markdown("### 📈 Log Returns nel Tempo")
    fig_returns = go.Figure()
    for col in prezzi_returns.columns:
            fig_returns.add_trace(go.Scatter(x=prezzi_returns.index, y=prezzi_returns[col], name=col))
    fig_returns.update_layout(title="Andamento Log Returns", xaxis_title="Data", yaxis_title="Log Return")
    st.plotly_chart(fig_returns, use_container_width=True)

    st.markdown("### 🔥 Heatmap di Correlazione")
    fig_corr = go.Figure(data=go.Heatmap(
            z=correlazione.values,
            x=correlazione.columns,
            y=correlazione.index,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlazione")
        ))
    fig_corr.update_layout(title="Heatmap Correlazione Log Returns")
    st.plotly_chart(fig_corr, use_container_width=True)

import os
import importlib
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Importa e recarrega o módulo de banco de dados
import database
importlib.reload(database)

# Configuração da página do Streamlit
st.set_page_config(
    page_title="OftalmoPlus - Dashboard de Telefonia",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada premium
st.markdown("""
<style>
    .main {
        background-color: #0B1120;
    }
    
    /* Cartões de Métricas */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9));
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
        transition: all 0.25s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: #3B82F6;
        box-shadow: 0 8px 24px -2px rgba(59, 130, 246, 0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-weight: 800;
        font-size: 1.85rem;
    }
    
    /* Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-live {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-sim {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .banner-card {
        background: rgba(30, 41, 59, 0.5);
        border-left: 4px solid #3B82F6;
        padding: 12px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3616/3616930.png", width=60)
    st.title("OftalmoPlus")
    st.caption("Central de Telefonia & Atendimento Integrado")
    st.divider()

    st.subheader("🔌 Conexão Supabase")
    url_env, key_env, default_table = database.get_credentials()

    # Informa o endpoint conectado
    if url_env:
        st.markdown(f"**Host:** `{url_env.replace('https://', '')}`")
    
    # Seleção de Tabela real do banco
    if hasattr(database, "get_available_tables"):
        available_tables = database.get_available_tables()
    else:
        available_tables = [
            "rel_consolidado_agentes",
            "relatorio_chamadas",
            "relatorio_geral_agentes",
            "tableid",
            "listar_agentes",
            "listar_ramais"
        ]
    current_index = 0
    if default_table in available_tables:
        current_index = available_tables.index(default_table)

    selected_table = st.selectbox(
        "Tabela Ativa no Supabase:",
        options=available_tables,
        index=current_index,
        help="Tabelas reais identificadas na sua instância do Supabase."
    )

    col_btn_test, col_btn_ref = st.columns(2)
    with col_btn_test:
        test_clicked = st.button("Testar ⚡", use_container_width=True)
    with col_btn_ref:
        refresh_clicked = st.button("Atualizar 🔄", use_container_width=True)

    if test_clicked:
        with st.spinner("Testando conexão..."):
            ok, msg, info = database.test_connection(selected_table)
            if ok:
                if info.get("has_rls_block"):
                    st.warning(msg)
                else:
                    st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.subheader("💡 Nota sobre RLS no Supabase")
    with st.expander("Ver detalhes de acesso"):
        st.markdown("""
        Se a tabela contiver dados no banco mas retornar 0 linhas:
        - A chave configurada no `.env` é do tipo **`anon`**.
        - Por padrão, o Postgres do Supabase bloqueia a chave pública com **RLS (Row Level Security)**.
        - **Para liberar:**
          1. Use a chave **`service_role`** no `.env` (que ignora o RLS), **OU**
          2. No Supabase SQL Editor, rode:
             ```sql
             ALTER TABLE public.""" + selected_table + """ ENABLE ROW LEVEL SECURITY;
             CREATE POLICY "Permitir leitura publica" 
             ON public.""" + selected_table + """ FOR SELECT TO anon USING (true);
             ```
        """)

# ----------------- BUSCA DOS DADOS -----------------
with st.spinner(f"Carregando dados de '{selected_table}'..."):
    df, is_real, status_message = database.fetch_data(table_name=selected_table)

    # Sanitização: converte colunas que contêm listas ou dicts (ex: arrays do PostgreSQL) em strings
    if df is not None and not df.empty:
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                df[col] = df[col].apply(
                    lambda x: ", ".join(map(str, x)) if isinstance(x, list) else (str(x) if isinstance(x, dict) else x)
                )

# ----------------- CABEÇALHO PRINCIPAL -----------------
head_col1, head_col2 = st.columns([3, 1])

with head_col1:
    st.title("👁️ Painel de Operações de Telefonia")
    st.markdown("Monitoramento de Agentes, Produtividade, Filas de Espera e Indicadores Oftalmológicos.")

with head_col2:
    st.write("")
    if is_real:
        st.markdown('<span class="status-badge badge-live">● Supabase (Dados Reais)</span>', unsafe_allow_html=True)
        st.caption(f"Tabela: `{selected_table}` • {len(df)} linhas")
    else:
        st.markdown('<span class="status-badge badge-sim">▲ Simulação (Schema Real)</span>', unsafe_allow_html=True)
        st.caption(f"Estrutura: `{selected_table}`")

if not is_real:
    st.info(f"ℹ️ {status_message}")

# ----------------- VISÃO POR TABELA ESPECÍFICA -----------------
if selected_table == "rel_consolidado_agentes" or ("calls_answered" in df.columns and "name" in df.columns):
    # === TABELA: REL_CONSOLIDADO_AGENTES ===
    
    # Filtro por Agente e Fila
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        if "name" in df.columns:
            agentes_op = ["Todos os Agentes"] + sorted(list(df["name"].dropna().unique()))
            sel_agente = st.selectbox("Filtrar por Agente:", agentes_op)
        else:
            sel_agente = "Todos os Agentes"
            
    with filter_col2:
        if "queues" in df.columns:
            filas_op = ["Todas as Filas"] + sorted(list(df["queues"].dropna().unique()))
            sel_fila = st.selectbox("Filtrar por Fila / Setor:", filas_op)
        else:
            sel_fila = "Todas as Filas"

    filtered_df = df.copy()
    if sel_agente != "Todos os Agentes" and "name" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["name"] == sel_agente]
    if sel_fila != "Todas as Filas" and "queues" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["queues"] == sel_fila]

    # KPIs Principais
    st.subheader("📊 Indicadores Gerais da Equipe")
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_calls = int(filtered_df["total_calls"].sum()) if "total_calls" in filtered_df.columns else len(filtered_df)
    ans_calls = int(filtered_df["calls_answered"].sum()) if "calls_answered" in filtered_df.columns else 0
    lost_calls = int(filtered_df["calls_lost"].sum()) if "calls_lost" in filtered_df.columns else 0
    
    tx_atendimento = f"{(ans_calls / max(1, total_calls)) * 100:.1f}%" if total_calls > 0 else "0.0%"
    tx_prod_in = f"{filtered_df['percent_productivity_in'].mean():.1f}%" if "percent_productivity_in" in filtered_df.columns else "N/A"
    total_agentes = len(filtered_df["name"].unique()) if "name" in filtered_df.columns else len(filtered_df)

    k1.metric("Total Chamadas", f"{total_calls:,}")
    k2.metric("Atendidas", f"{ans_calls:,}")
    k3.metric("Perdidas", f"{lost_calls:,}")
    k4.metric("Taxa Atendimento", tx_atendimento)
    k5.metric("Produtividade In", tx_prod_in)
    k6.metric("Agentes Ativos", f"{total_agentes}")

    st.write("")
    
    # Gráficos da Equipe
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        if "name" in filtered_df.columns and "calls_answered" in filtered_df.columns:
            fig_bar = px.bar(
                filtered_df,
                x="name",
                y=["calls_answered", "calls_lost"],
                title="Chamadas Atendidas vs Perdidas por Agente",
                barmode="group",
                labels={"value": "Quantidade", "name": "Agente", "variable": "Tipo"},
                color_discrete_map={"calls_answered": "#10B981", "calls_lost": "#EF4444"}
            )
            fig_bar.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 23, 42, 0.4)",
                plot_bgcolor="rgba(15, 23, 42, 0)",
                legend_title_text="Status"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with g_col2:
        if "name" in filtered_df.columns and "percent_productivity_in" in filtered_df.columns:
            fig_prod = px.bar(
                filtered_df.sort_values(by="percent_productivity_in", ascending=True),
                x="percent_productivity_in",
                y="name",
                orientation="h",
                title="Índice de Produtividade (%) por Agente",
                labels={"percent_productivity_in": "Produtividade Entrante (%)", "name": "Agente"},
                color="percent_productivity_in",
                color_continuous_scale="Teal"
            )
            fig_prod.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 23, 42, 0.4)",
                plot_bgcolor="rgba(15, 23, 42, 0)",
                xaxis=dict(range=[0, 105])
            )
            st.plotly_chart(fig_prod, use_container_width=True)

    # Gráfico de Proporção Entrante vs Sainte
    if "total_calls_in" in filtered_df.columns and "total_calls_out" in filtered_df.columns:
        g2_c1, g2_c2 = st.columns([1, 2])
        with g2_c1:
            tot_in = filtered_df["total_calls_in"].sum()
            tot_out = filtered_df["total_calls_out"].sum()
            fig_pie = px.pie(
                values=[tot_in, tot_out],
                names=["Entrantes (Pacientes)", "Saintes (Atendentes)"],
                title="Proporção de Fluxo de Chamadas",
                hole=0.55,
                color_discrete_sequence=["#3B82F6", "#8B5CF6"]
            )
            fig_pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 23, 42, 0.4)",
                plot_bgcolor="rgba(15, 23, 42, 0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with g2_c2:
            if "queues" in filtered_df.columns:
                queue_summary = filtered_df.groupby("queues")[["calls_answered", "calls_lost"]].sum().reset_index()
                fig_queue = px.bar(
                    queue_summary,
                    x="queues",
                    y=["calls_answered", "calls_lost"],
                    title="Volume por Setor / Fila de Atendimento",
                    barmode="stack",
                    labels={"value": "Total de Chamadas", "queues": "Setor"},
                    color_discrete_map={"calls_answered": "#3B82F6", "calls_lost": "#F59E0B"}
                )
                fig_queue.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(15, 23, 42, 0.4)",
                    plot_bgcolor="rgba(15, 23, 42, 0)"
                )
                st.plotly_chart(fig_queue, use_container_width=True)

elif selected_table == "relatorio_chamadas" or ("agent_name" in df.columns and "disposition" in df.columns):
    # === TABELA: RELATORIO_CHAMADAS ===
    st.subheader("📞 Registro Detalhado de Ligações")

    c1, c2, c3, c4 = st.columns(4)
    total_calls = len(df)
    atendidas = (df["disposition"] == "ANSWERED").sum() if "disposition" in df.columns else 0
    tma_seg = int(df["ta"].mean()) if "ta" in df.columns else 0
    tme_seg = int(df["teu"].mean()) if "teu" in df.columns else 0

    c1.metric("Total Chamadas", f"{total_calls:,}")
    c2.metric("Atendidas", f"{atendidas:,}")
    c3.metric("Tempo Médio Atend. (TMA)", f"{tma_seg // 60}m {tma_seg % 60}s")
    c4.metric("Tempo Médio Espera (TME)", f"{tme_seg // 60}m {tme_seg % 60}s")

    st.write("")
    rc1, rc2 = st.columns(2)
    with rc1:
        if "disposition" in df.columns:
            fig_disp = px.pie(
                df,
                names="disposition",
                title="Desfecho das Chamadas (Disposition)",
                hole=0.5,
                color_discrete_sequence=["#10B981", "#EF4444", "#F59E0B", "#6B7280"]
            )
            fig_disp.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 23, 42, 0.4)",
                plot_bgcolor="rgba(15, 23, 42, 0)"
            )
            st.plotly_chart(fig_disp, use_container_width=True)

    with rc2:
        if "queuename" in df.columns:
            fila_counts = df["queuename"].value_counts().reset_index()
            fila_counts.columns = ["Fila", "Chamadas"]
            fig_f = px.bar(
                fila_counts,
                x="Chamadas",
                y="Fila",
                orientation="h",
                title="Chamadas por Fila / Serviço",
                color="Chamadas",
                color_continuous_scale="Purples"
            )
            fig_f.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 23, 42, 0.4)",
                plot_bgcolor="rgba(15, 23, 42, 0)"
            )
            st.plotly_chart(fig_f, use_container_width=True)
    filtered_df = df

else:
    # === TABELA GENÉRICA / OUTRAS TABELAS ===
    st.subheader(f"📋 Visualização dos Dados: `{selected_table}`")
    filtered_df = df

# ----------------- TABELA COMPLETA COM EXPORTAÇÃO -----------------
st.subheader("📋 Tabela Consolidada de Registros")
with st.expander("Expandir visualização da tabela e download", expanded=True):
    col_exp1, col_exp2 = st.columns([4, 1])
    with col_exp2:
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar CSV 📥",
            data=csv,
            file_name=f"{selected_table}_oftalmoplus.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")
st.caption("OftalmoPlus • Conexão Oficial Supabase • Desenvolvido com Streamlit e Python")

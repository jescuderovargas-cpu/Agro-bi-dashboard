import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Gestión de Rentabilidad Agro", layout="wide")

# --- ESTILO MEJORADO: DISEÑO PLANO SIN BLOQUES OSCUROS (IDEAL MÓVIL) ---
st.markdown("""
    <style>
    /* Métricas principales en Negro */
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 1.8rem !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 500; }
    
    /* Títulos en Negro */
    h3 { color: #000000; padding-bottom: 5px; font-size: 1.2rem !important; margin-top: 15px; font-weight: 700; }

    /* --- DISEÑO DE PESTAÑAS (TABS) TIPO UNDERLINE --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent !important;
        border: none !important;
        color: #666666 !important;
        font-weight: 400;
        transition: all 0.2s ease;
    }

    /* Pestaña seleccionada: Texto en verde y línea inferior (Sin fondo oscuro) */
    .stTabs [aria-selected="true"] { 
        color: #2e7d32 !important; 
        font-weight: 700 !important;
        border-bottom: 3px solid #2e7d32 !important;
        background-color: transparent !important;
    }

    /* Quitar efectos de sombreado negro al tocar en móvil */
    .stTabs [data-baseweb="tab"]:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    /* Ajuste de filtros laterales */
    .stMultiSelect label { color: #000000 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def form(val, precision=2):
    if precision == 0: return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.{precision}f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def cargar_datos():
    if os.path.exists("datos_acl.xlsx"):
        df = pd.read_excel("datos_acl.xlsx")
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    return None

df_raw = cargar_datos()

if df_raw is not None:
    # --- BARRA LATERAL ---
    st.sidebar.header("PANEL DE CONTROL")
    sel_sem = st.sidebar.multiselect("Semanas", sorted(df_raw['fecha_semana'].unique()), default=sorted(df_raw['fecha_semana'].unique()))
    sel_fam = st.sidebar.multiselect("Familias", sorted(df_raw['familia'].unique()), default=sorted(df_raw['familia'].unique()))
    sel_cli = st.sidebar.multiselect("Clientes", sorted(df_raw['cliente'].unique()), default=sorted(df_raw['cliente'].unique()))

    # Filtros
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    df_op = df_f[~is_rr & ~df_f['articulo'].astype(str).str.contains("II", case=False) & ~df_f['cliente'].astype(str).str.contains("Tirado", case=False)]
    df_reclamaciones = df_f[is_rr]
    df_seg_tir = df_f[df_f['articulo'].astype(str).str.contains("II", case=False) | df_f['cliente'].astype(str).str.contains("Tirado", case=False)]

    # Cálculos
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    t_g_almacen = df_op[['estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo']].sum().sum()
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + t_g_almacen + t_ope)
    margen_kg_global = beneficio_neto / t_kg_e if t_kg_e > 0 else 0

    # --- UI ---
    st.markdown("### Rendimiento Económico Neto")
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Beneficio Neto Total", f"{form(beneficio_neto)} €")
    kpi2.metric("Margen Neto por KG", f"{form(margen_kg_global, 4)} €/kg")
    st.markdown("---")

    tabs = st.tabs(["RESUMEN DE NEGOCIO", "SEGUNDAS Y TIRADO", "RECLAMACIONES"])

    with tabs[0]:
        st.markdown("### Volumen y Facturación")
        f1, f2, f3 = st.columns(3)
        f1.metric("Facturación Total", f"{form(t_vta)} €")
        f2.metric("Kilos Enviados", f"{form(t_kg_e, 0)} kg")
        sobrepeso = t_kg_e - df_op['pesonetovendido'].sum()
        f3.metric("Sobrepeso (Merma)", f"{form(sobrepeso, 0)} kg", delta=f"{form((sobrepeso/t_kg_e*100) if t_kg_e>0 else 0, 2)}% s/env", delta_color="inverse")

        st.markdown("### Desglose de Gastos de Almacén (€/kg)")
        dg1, dg2, dg3, dg4, dg5 = st.columns(5)
        dg1.metric("Estructura", f"{form(df_op['estruct'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg2.metric("Mano Obra", f"{form(df_op['mano_obra'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg3.metric("Envase", f"{form(df_op['c_envase'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg4.metric("Palet", f"{form(df_op['c_palet'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg5.metric("Bolsa/Otros", f"{form(df_op['cbo'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")

        st.markdown("---")
        st.markdown("### Evolución del Margen Neto Semanal")
        df_sem = df_op.groupby('fecha_semana').agg({
            'pesonetoenviado': 'sum', 'venta_neta': 'sum', 'importecompra': 'sum',
            'estruct': 'sum', 'mano_obra': 'sum', 'c_envase': 'sum', 'c_palet': 'sum', 'cbo': 'sum',
            'comision': 'sum', 'porte_orig': 'sum', 'porte_dest': 'sum'
        }).reset_index()
        df_sem['gastos_totales'] = df_sem[['importecompra', 'estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo', 'comision', 'porte_orig', 'porte_dest']].sum(axis=1)
        df_sem['margen_neto_kg'] = (df_sem['venta_neta'] - df_sem['gastos_totales']) / df_sem['pesonetoenviado']
        
        fig_evol = px.line(df_sem, x='fecha_semana', y='margen_neto_kg', markers=True, color_discrete_sequence=['#2e7d32'])
        fig_evol.update_layout(yaxis_tickformat='.2f')
        st.plotly_chart(fig_evol, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.bar(df_op.groupby('familia')['venta_neta'].sum().reset_index(), x='familia', y='venta_neta', color='familia', color_discrete_sequence=px.colors.qualitative.Bold), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df_op, values='pesonetovendido', names='familia', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)

    with tabs[1]:
        st.markdown("### Mermas: Segundas y Tirado")
        s1, s2 = st.columns(2)
        mask_seg = df_seg_tir['articulo'].astype(str).str.contains("II", case=False)
        mask_tir = df_seg_tir['cliente'].astype(str).str.contains("Tirado", case=False)
        s1.metric("KG Segundas (II)", f"{form(df_seg_tir[mask_seg]['pesonetovendido'].sum(), 0)} kg")
        s2.metric("KG Tirado", f"{form(df_seg_tir[mask_tir]['pesonetovendido'].sum(), 0)} kg")
        if not df_seg_tir.empty:
            st.plotly_chart(px.bar(df_seg_tir.groupby('familia')['pesonetovendido'].sum().reset_index(), x='familia', y='pesonetovendido', color='familia', color_discrete_sequence=px.colors.qualitative.Prism), use_container_width=True)

    with tabs[2]:
        st.markdown("### Reclamaciones y Abonos")
        st.metric("Total Reclamado", f"{form(df_reclamaciones['venta_neta'].sum())} €")
        if not df_reclamaciones.empty:
            top_r = df_reclamaciones.groupby('cliente')['venta_neta'].sum().reset_index().sort_values('venta_neta').head(5)
            st.plotly_chart(px.bar(top_r, x='venta_neta', y='cliente', orientation='h', color='cliente', color_discrete_sequence=px.colors.sequential.Reds_r), use_container_width=True)

else:
    st.error("Archivo no detectado.")

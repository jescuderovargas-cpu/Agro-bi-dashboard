import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Gestión de Rentabilidad Agro", layout="wide")

# --- ESTILO ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 1.8rem !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 500; }
    h3 { color: #000000; padding-bottom: 5px; font-size: 1.2rem !important; margin-top: 15px; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent !important; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: transparent !important; color: #666666 !important; }
    .stTabs [aria-selected="true"] { color: #2e7d32 !important; font-weight: 700 !important; border-bottom: 3px solid #2e7d32 !important; }
    </style>
""", unsafe_allow_html=True)

def form(val, precision=2):
    if precision == 0: return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.{precision}f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data
def cargar_datos():
    if os.path.exists("datos_acl.xlsx"):
        df = pd.read_excel("datos_acl.xlsx")
        # LIMPIEZA CRÍTICA: Quitamos espacios vacíos y pasamos a minúsculas
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    return None

df_raw = cargar_datos()

if df_raw is not None:
    # --- PANEL LATERAL ---
    st.sidebar.header("PANEL DE CONTROL")
    sel_sem = st.sidebar.multiselect("Semanas", sorted(df_raw['fecha_semana'].unique()), default=sorted(df_raw['fecha_semana'].unique()))
    sel_fam = st.sidebar.multiselect("Familias", sorted(df_raw['familia'].unique()), default=sorted(df_raw['familia'].unique()))
    sel_cli = st.sidebar.multiselect("Clientes", sorted(df_raw['cliente'].unique()), default=sorted(df_raw['cliente'].unique()))

    # --- APLICACIÓN DE FILTROS (Esto hace que el panel cambie) ---
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    is_tirado = df_f['cliente'].astype(str).str.contains("Tirado", case=False)
    is_segunda = df_f['articulo'].astype(str).str.contains("II", case=False)

    # Definición de DataFrames filtrados
    df_op = df_f[~is_rr & ~is_segunda & ~is_tirado]
    df_seg_tir = df_f[is_segunda | is_tirado]
    df_reclamaciones = df_f[is_rr & ~is_tirado]

    # --- CÁLCULOS SOBRE LOS DATOS FILTRADOS ---
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_kg_v = df_op['pesonetovendido'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    
    # Precios Medios
    pm_vta = t_vta / t_kg_v if t_kg_v > 0 else 0
    pm_com = t_com / t_kg_v if t_kg_v > 0 else 0
    
    # GASTOS ALMACÉN (Aquí es donde se suma la mano de obra)
    # Usamos .get() por seguridad si la columna no existiera
    val_mano_obra = df_op['mano_obra'].sum() if 'mano_obra' in df_op.columns else 0
    sum_g_almacen = df_op[['estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo']].sum().sum()
    ratio_g_almacen = sum_g_almacen / t_kg_e if t_kg_e > 0 else 0
    
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + sum_g_almacen + t_ope)
    margen_kg_global = beneficio_neto / t_kg_e if t_kg_e > 0 else 0

    # --- UI ---
    st.markdown("### Rendimiento Económico Neto")
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Beneficio Neto Total", f"{form(beneficio_neto)} €")
    kpi2.metric("Margen Neto Final", f"{form(margen_kg_global, 4)} €/kg")
    
    tabs = st.tabs(["RESUMEN DE NEGOCIO", "SEGUNDAS Y TIRADO", "RECLAMACIONES"])

    with tabs[0]:
        st.markdown("### Volumen y Facturación")
        vf1, vf2, vf3, vf4 = st.columns(4)
        vf1.metric("Facturación", f"{form(t_vta)} €")
        vf2.metric("Kg Vendidos", f"{form(t_kg_v, 0)} kg")
        vf3.metric("Kg Enviados", f"{form(t_kg_e, 0)} kg")
        sobrepeso = t_kg_e - t_kg_v
        vf4.metric("Mermas", f"{form(sobrepeso, 0)} kg")

        st.markdown("### Precios Medios (€/kg)")
        pm1, pm2 = st.columns(2)
        pm1.metric("P. Medio Venta", f"{form(pm_vta, 3)} €/kg")
        pm2.metric("P. Medio Compra", f"{form(pm_com, 3)} €/kg")

        # DESGLOSE DINÁMICO
        st.markdown(f"### Desglose Gastos Almacén ({form(ratio_g_almacen, 3)} €/kg)")
        dg1, dg2, dg3, dg4, dg5 = st.columns(5)
        dg1.metric("Estructura", f"{form(df_op['estruct'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        
        # AQUÍ ESTÁ LA MANO DE OBRA
        dg2.metric("Mano Obra", f"{form(val_mano_obra/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        
        dg3.metric("Envase", f"{form(df_op['c_envase'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg4.metric("Palet", f"{form(df_op['c_palet'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg5.metric("Bolsa/Otros", f"{form(df_op['cbo'].sum()/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")

        st.markdown("---")
        st.markdown("### Evolución del Margen Semanal")
        df_sem = df_op.groupby('fecha_semana').agg({
            'pesonetoenviado': 'sum', 'venta_neta': 'sum', 'importecompra': 'sum',
            'estruct': 'sum', 'mano_obra': 'sum', 'c_envase': 'sum', 'c_palet': 'sum', 'cbo': 'sum',
            'comision': 'sum', 'porte_orig': 'sum', 'porte_dest': 'sum'
        }).reset_index()
        df_sem['gastos_totales'] = df_sem[['importecompra', 'estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo', 'comision', 'porte_orig', 'porte_dest']].sum(axis=1)
        df_sem['margen_neto_kg'] = (df_sem['venta_neta'] - df_sem['gastos_totales']) / df_sem['pesonetoenviado']
        
        fig_evol = px.line(df_sem, x='fecha_semana', y='margen_neto_kg', markers=True, color_discrete_sequence=['#2e7d32'])
        st.plotly_chart(fig_evol, use_container_width=True)

else:
    st.error("No se ha podido cargar el archivo 'datos_acl.xlsx'.")

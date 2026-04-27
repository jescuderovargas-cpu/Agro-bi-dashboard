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
        # Limpieza profunda de nombres de columnas
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df
    return None

df_raw = cargar_datos()

if df_raw is not None:
    # --- PANEL LATERAL ---
    st.sidebar.header("PANEL DE CONTROL")
    
    # Aseguramos que los selectores siempre tengan datos frescos
    opciones_sem = sorted(df_raw['fecha_semana'].unique())
    opciones_fam = sorted(df_raw['familia'].unique())
    opciones_cli = sorted(df_raw['cliente'].unique())
    
    sel_sem = st.sidebar.multiselect("Semanas", opciones_sem, default=opciones_sem)
    sel_fam = st.sidebar.multiselect("Familias", opciones_fam, default=opciones_fam)
    sel_cli = st.sidebar.multiselect("Clientes", opciones_cli, default=opciones_cli)

    # --- FILTRADO REAL-TIME ---
    # Creamos una copia filtrada en cada ejecución (sin caché aquí para que cambie el número)
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    mask_rr = df_f['alb_str'].str.contains("RR", case=False)
    mask_tirado = df_f['cliente'].astype(str).str.contains("Tirado", case=False)
    mask_segunda = df_f['articulo'].astype(str).str.contains("II", case=False)

    # Segmentación basada en el filtro actual
    df_op = df_f[~mask_rr & ~mask_segunda & ~mask_tirado]
    df_seg_tir = df_f[mask_segunda | mask_tirado]
    df_reclamaciones = df_f[mask_rr & ~mask_tirado]

    # --- CÁLCULOS CRÍTICOS (DEPENDIENTES DEL FILTRO) ---
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_kg_v = df_op['pesonetovendido'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    
    # GASTOS ALMACÉN (Recalculados al instante)
    # Buscamos la columna con seguridad
    col_mo = 'mano_obra' if 'mano_obra' in df_op.columns else None
    
    g_est = df_op['estruct'].sum()
    g_mo = df_op[col_mo].sum() if col_mo else 0
    g_env = df_op['c_envase'].sum()
    g_pal = df_op['c_palet'].sum()
    g_cbo = df_op['cbo'].sum() if 'cbo' in df_op.columns else (df_op['c_bo'].sum() if 'c_bo' in df_op.columns else 0)
    
    sum_g_almacen = g_est + g_mo + g_env + g_pal + g_cbo
    ratio_g_almacen = sum_g_almacen / t_kg_e if t_kg_e > 0 else 0
    
    # Margen
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + sum_g_almacen + t_ope)
    margen_kg_global = beneficio_neto / t_kg_e if t_kg_e > 0 else 0

    # --- INTERFAZ ---
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
        vf4.metric("Mermas (Kg)", f"{form(t_kg_e - t_kg_v, 0)} kg")

        st.markdown("### Precios Medios (€/kg)")
        pm_col1, pm_col2 = st.columns(2)
        pm_col1.metric("P. Medio Venta", f"{form(t_vta/t_kg_v if t_kg_v > 0 else 0, 3)} €/kg")
        pm_col2.metric("P. Medio Compra", f"{form(t_com/t_kg_v if t_kg_v > 0 else 0, 3)} €/kg")

        # DESGLOSE DE GASTOS (Aquí verás el cambio en Mano de Obra)
        st.markdown(f"### Desglose Gastos Almacén ({form(ratio_g_almacen, 3)} €/kg)")
        dg1, dg2, dg3, dg4, dg5 = st.columns(5)
        dg1.metric("Estructura", f"{form(g_est/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg2.metric("Mano Obra", f"{form(g_mo/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg3.metric("Envase", f"{form(g_env/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg4.metric("Palet", f"{form(g_pal/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        dg5.metric("Bolsa/Otros", f"{form(g_cbo/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")

        st.markdown("---")
        st.markdown("### Evolución del Margen Semanal")
        df_sem = df_op.groupby('fecha_semana').agg({
            'pesonetoenviado': 'sum', 'venta_neta': 'sum', 'importecompra': 'sum',
            'estruct': 'sum', 'mano_obra': 'sum', 'c_envase': 'sum', 'c_palet': 'sum',
            'comision': 'sum', 'porte_orig': 'sum', 'porte_dest': 'sum'
        }).reset_index()
        
        # Cálculo del margen semanal para el gráfico
        df_sem['gastos'] = df_sem[['importecompra', 'estruct', 'mano_obra', 'c_envase', 'c_palet', 'comision', 'porte_orig', 'porte_dest']].sum(axis=1)
        df_sem['margen_kg'] = (df_sem['venta_neta'] - df_sem['gastos']) / df_sem['pesonetoenviado']
        st.plotly_chart(px.line(df_sem, x='fecha_semana', y='margen_kg', markers=True, color_discrete_sequence=['#2e7d32']), use_container_width=True)

    with tabs[1]:
        st.markdown("### Análisis de Segundas y Tirado")
        s1, s2 = st.columns(2)
        s1.metric("Total Segundas (II)", f"{form(df_seg_tir[mask_segunda]['pesonetovendido'].sum(), 0)} kg")
        s2.metric("Total Tirado", f"{form(df_seg_tir[mask_tirado]['pesonetovendido'].sum(), 0)} kg")
        
        if not df_seg_tir.empty:
            fig_seg = px.bar(df_seg_tir.groupby('familia')['pesonetovendido'].sum().reset_index(), x='familia', y='pesonetovendido', color='familia')
            st.plotly_chart(fig_seg, use_container_width=True)

    with tabs[2]:
        st.markdown("### Reclamaciones y Abonos (RR)")
        st.metric("Importe Reclamado", f"{form(df_reclamaciones['venta_neta'].sum())} €")
        if not df_reclamaciones.empty:
            df_rec_cli = df_reclamaciones.groupby('cliente')['venta_neta'].sum().reset_index().sort_values('venta_neta', ascending=False)
            st.plotly_chart(px.bar(df_rec_cli, x='cliente', y='venta_neta', color='venta_neta', color_continuous_scale='Reds'), use_container_width=True)

else:
    st.error("No se detecta el archivo 'datos_acl.xlsx'.")

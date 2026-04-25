import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Gestión de Rentabilidad Agro", layout="wide")

# --- ESTILO LIMPIO ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #1B5E20 !important; font-size: 1.8rem !important; }
    h3 { color: #333333; padding-bottom: 5px; font-size: 1.2rem !important; margin-top: 15px; }
    .stTabs [aria-selected="true"] { background-color: #f0f2f6 !important; border-radius: 5px; }
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
    # --- FILTROS ---
    st.sidebar.header("FILTROS")
    sel_sem = st.sidebar.multiselect("Semanas", sorted(df_raw['fecha_semana'].unique()), default=sorted(df_raw['fecha_semana'].unique()))
    sel_fam = st.sidebar.multiselect("Familias", sorted(df_raw['familia'].unique()), default=sorted(df_raw['familia'].unique()))
    sel_cli = st.sidebar.multiselect("Clientes", sorted(df_raw['cliente'].unique()), default=sorted(df_raw['cliente'].unique()))

    # Aplicación de filtros
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    
    # Procesamiento de subconjuntos
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    df_op = df_f[~is_rr & ~df_f['articulo'].astype(str).str.contains("II", case=False) & ~df_f['cliente'].astype(str).str.contains("Tirado", case=False)]
    df_reclamaciones = df_f[is_rr]
    df_seg_tir = df_f[df_f['articulo'].astype(str).str.contains("II", case=False) | df_f['cliente'].astype(str).str.contains("Tirado", case=False)]

    # Cálculos globales
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    t_alm = df_op[['estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo']].sum().sum()
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + t_alm + t_ope)
    margen_kg = beneficio_neto / t_kg_e if t_kg_e > 0 else 0

    # --- RESULTADO PRINCIPAL (ARRIBA DE TODO) ---
    st.markdown("### Rendimiento Económico Neto")
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Beneficio Neto Total", f"{form(beneficio_neto)} €")
    kpi2.metric("Margen Neto por KG", f"{form(margen_kg, 4)} €/kg")
    st.markdown("---")

    tabs = st.tabs(["RESUMEN DE NEGOCIO", "SEGUNDAS Y TIRADO", "RECLAMACIONES"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Kilos Enviados", f"{form(t_kg_e, 0)} kg")
        sobrepeso = t_kg_e - df_op['pesonetovendido'].sum()
        c2.metric("Sobrepeso (Merma)", f"{form(sobrepeso, 0)} kg")
        c3.metric("Gastos Almacén", f"{form(t_alm)} €")

        st.markdown("### Análisis de Precios")
        p1, p2 = st.columns(2)
        p1.metric("Precio Venta Medio", f"{form(t_vta/t_kg_e if t_kg_e>0 else 0)} €/kg")
        p2.metric("Precio Compra Medio", f"{form(t_com/t_kg_e if t_kg_e>0 else 0)} €/kg")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(px.bar(df_op.groupby('familia')['venta_neta'].sum().reset_index(), x='familia', y='venta_neta', title="Facturación por Familia", color_discrete_sequence=['#2E7D32']), use_container_width=True)
        with col_g2:
            st.plotly_chart(px.pie(df_op, values='pesonetovendido', names='familia', title="Volumen por Familia", hole=0.4), use_container_width=True)

        with st.expander("VER TABLA DE DATOS"):
            st.dataframe(df_op[['fecha_semana', 'familia', 'cliente', 'articulo', 'pesonetovendido', 'venta_neta']], use_container_width=True)

    with tabs[1]:
        st.markdown("### Análisis de Segundas y Tirado")
        mask_seg = df_seg_tir['articulo'].astype(str).str.contains("II", case=False)
        mask_tir = df_seg_tir['cliente'].astype(str).str.contains("Tirado", case=False)
        
        s1, s2 = st.columns(2)
        kg_seg = df_seg_tir[mask_seg]['pesonetovendido'].sum()
        kg_tir = df_seg_tir[mask_tir]['pesonetovendido'].sum()
        s1.metric("KG Segundas (II)", f"{form(kg_seg, 0)} kg")
        s2.metric("KG Tirado", f"{form(kg_tir, 0)} kg")

        if not df_seg_tir.empty:
            st.plotly_chart(px.bar(df_seg_tir.groupby('familia')['pesonetovendido'].sum().reset_index(), x='familia', y='pesonetovendido', title="Mermas por Familia", color='familia'), use_container_width=True)
            st.dataframe(df_seg_tir[['fecha_semana', 'familia', 'cliente', 'articulo', 'pesonetovendido', 'venta_neta']], use_container_width=True)
        else:
            st.info("No hay datos de segundas o tirado con los filtros seleccionados.")

    with tabs[2]:
        st.markdown("### Reclamaciones (Abonos)")
        total_rr = df_reclamaciones['venta_neta'].sum()
        st.metric("Total Importe Reclamado", f"{form(total_rr)} €")
        
        if not df_reclamaciones.empty:
            st.dataframe(df_reclamaciones[['fecha_semana', 'familia', 'cliente', 'venta_neta']].sort_values('venta_neta'), use_container_width=True)
        else:
            st.info("No hay reclamaciones registradas en este periodo.")

else:
    st.error("No se ha encontrado el archivo de datos.")

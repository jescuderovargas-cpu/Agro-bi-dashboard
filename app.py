import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Demo BI - Gestión Agrícola", layout="wide")

# --- ESTILO CORPORATIVO ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #2E7D32 !important; font-size: 1.5rem !important; }
    h3 { color: #333333; background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 1.1rem !important; margin-top: 20px; border-left: 5px solid #2E7D32; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eeeeee; }
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
    # --- FILTROS LATERALES ---
    st.sidebar.header("FILTROS DE CAMPAÑA")
    op_sem = sorted(df_raw['fecha_semana'].unique())
    sel_sem = st.sidebar.multiselect("Semanas", op_sem, default=op_sem)
    op_fam = sorted(df_raw['familia'].unique())
    sel_fam = st.sidebar.multiselect("Familias", op_fam, default=op_fam)
    op_cli = sorted(df_raw['cliente'].unique())
    sel_cli = st.sidebar.multiselect("Clientes", op_cli, default=op_cli)

    # Aplicar filtros
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    df_seg_tir_raw = df_f.copy()
    
    # Datos para Rentabilidad (Limpieza de calidad)
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    df_clean = df_f[is_rr | ~df_f['articulo'].astype(str).str.contains("II", case=False)]
    df_clean = df_clean[~df_clean['cliente'].astype(str).str.contains("Tirado", case=False)]
    df_op = df_clean[~is_rr]
    df_special = df_clean[is_rr]

    # --- CÁLCULOS ---
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_kg_v = df_op['pesonetovendido'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    
    # Gastos Almacén
    g_estruct = df_op['estruct'].sum()
    g_m_obra = df_op['mano_obra'].sum()
    g_envase = df_op['c_envase'].sum()
    g_palet = df_op['c_palet'].sum()
    g_bolsa = df_op['cbo'].sum()
    t_g_almacen = g_estruct + g_m_obra + g_envase + g_palet + g_bolsa
    
    # Gastos Operativos
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    
    beneficio_neto = t_vta - (t_com + t_g_almacen + t_ope)

    tabs = st.tabs(["RESUMEN DE NEGOCIO", "SEGUNDAS Y TIRADO", "RECLAMACIONES"])

    with tabs[0]:
        # 1. VOLUMEN Y SOBREPESOS
        st.markdown("### Volumen y Sobrepesos")
        c1, c2, c3 = st.columns(3)
        c1.metric("KG Enviados", f"{form(t_kg_e, 0)} kg")
        c2.metric("KG Vendidos", f"{form(t_kg_v, 0)} kg")
        sobrepeso = t_kg_e - t_kg_v
        porc_sobrepeso = (sobrepeso / t_kg_e * 100) if t_kg_e > 0 else 0
        c3.metric("Sobrepeso (Merma)", f"{form(sobrepeso, 0)} kg", delta=f"{form(porc_sobrepeso, 2)}%", delta_color="inverse")

        # 2. PRECIOS MEDIOS Y RENTABILIDAD
        st.markdown("### Precios Medios y Rentabilidad")
        p1, p2, p3 = st.columns(3)
        # Precios medios calculados sobre KG Enviados para ver impacto real
        p_vta_medio = t_vta / t_kg_e if t_kg_e > 0 else 0
        p_com_medio = t_com / t_kg_e if t_kg_e > 0 else 0
        p1.metric("P. Venta Medio", f"{form(p_vta_medio, 2)} €/kg")
        p2.metric("P. Compra Medio", f"{form(p_com_medio, 2)} €/kg")
        p3.metric("Margen Neto Total", f"{form(beneficio_neto)} €")

        # 3. DESGLOSE GASTOS DE ALMACÉN
        st.markdown(f"### Gastos de Almacén (Total: {form(t_g_almacen)} €)")
        g1, g2, g3, g4, g5 = st.columns(5)
        # Mostramos el coste por kilo de cada partida
        g1.metric("Estructura", f"{form(g_estruct/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        g2.metric("Mano Obra", f"{form(g_m_obra/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        g3.metric("Envase", f"{form(g_envase/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        g4.metric("Palet", f"{form(g_palet/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")
        g5.metric("Bolsa/Otros", f"{form(g_bolsa/t_kg_e if t_kg_e>0 else 0, 3)} €/kg")

        # GRÁFICOS
        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(px.bar(df_op.groupby('familia')['venta_neta'].sum().reset_index(), 
                                   x='familia', y='venta_neta', title="Ventas Totales por Familia", color_discrete_sequence=['#2E7D32']), use_container_width=True)
        with col_g2:
            st.plotly_chart(px.pie(df_op, values='pesonetovendido', names='familia', title="Distribución de Volumen", hole=0.4), use_container_width=True)

        # TABLA DE DATOS
        with st.expander("VER DETALLE DE OPERACIONES"):
            st.dataframe(df_op[['fecha_semana', 'familia', 'cliente', 'pesonetoenviado', 'pesonetovendido', 'venta_neta']], use_container_width=True)

    with tabs[1]:
        # (Contenido de Segundas y Tirado igual al anterior...)
        st.markdown("### Control de Segundas y Tirado")
        # ... (código previo)
        pass

    with tabs[2]:
        # (Contenido de Reclamaciones igual al anterior...)
        pass

else:
    st.error("Archivo 'datos_acl.xlsx' no encontrado.")

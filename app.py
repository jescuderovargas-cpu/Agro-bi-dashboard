import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Demo Business Intelligence - Agro", layout="wide")

# --- ESTILO PARA LA DEMO ---
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    [data-testid="stMetricValue"] { color: #2E7D32 !important; font-size: 1.8rem !important; }
    h1 { color: #1B5E20; border-bottom: 2px solid #1B5E20; padding-bottom: 10px; }
    .demo-header { background-color: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 25px; border: 1px solid #c8e6c9; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Panel de Control Logístico & Rentabilidad")

st.markdown("""
<div class="demo-header">
    <strong>Bienvenido a la versión Demo.</strong><br>
    Esta aplicación resuelve el problema de visibilidad en empresas agrícolas, permitiendo cruzar costes de almacén, 
    transportes y liquidaciones en tiempo real para obtener el <strong>beneficio neto por kg</strong>.
</div>
""", unsafe_allow_html=True)

def form(val, precision=2):
    if precision == 0: return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.{precision}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    if os.path.exists("datos_acl.xlsx"):
        df = pd.read_excel("datos_acl.xlsx")
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    return None

df_raw = cargar_datos()

if df_raw is not None:
    # Sidebar comercial
    st.sidebar.header("🎯 Filtros Interactivos")
    semanas = sorted(df_raw['fecha_semana'].unique())
    sel_sem = st.sidebar.multiselect("Filtrar Semanas", semanas, default=semanas)
    
    # Procesamiento
    df_f = df_raw[df_raw['fecha_semana'].isin(sel_sem)]
    df_f['alb_str'] = df_f['alb'].astype(str)
    
    # Guardamos copia para la pestaña de "Segundas" ANTES de limpiar
    df_seg_tir_raw = df_f[df_f['alb_str'].str.contains("s26", case=False)].copy()
    
    # Limpieza para el análisis de rentabilidad principal (Solo Primera)
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    df_clean = df_f[is_rr | ~df_f['articulo'].astype(str).str.contains("II", case=False)]
    df_clean = df_clean[~df_clean['cliente'].astype(str).str.contains("tirado", case=False)]
    
    df_op = df_clean[~is_rr]
    df_special = df_clean[is_rr]

    # Cálculos
    t_kg_v = df_op['pesonetovendido'].sum()
    t_kg_e = df_op['pesonetoenviado'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    t_alm = df_op[['estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo']].sum().sum()
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + t_alm + t_ope)

    tabs = st.tabs(["📈 RESUMEN DE NEGOCIO", "📦 SEGUNDAS Y TIRADO", "⚠️ RECLAMACIONES"])

    with tabs[0]:
        st.markdown("### Rentabilidad Neta Actual")
        m1, m2, m3 = st.columns(3)
        m1.metric("Kilos Vendidos", f"{form(t_kg_v, 0)} kg")
        m2.metric("Beneficio Neto Total", f"{form(beneficio_neto)} €")
        m3.metric("Margen Real / Kg", f"{form(beneficio_neto/t_kg_v, 4) if t_kg_v>0 else 0} €/kg")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.bar(df_op.groupby('familia')['venta_neta'].sum().reset_index(), 
                                   x='familia', y='venta_neta', title="Facturación por Familia", color='familia'), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df_op, values='pesonetovendido', names='familia', hole=0.4, title="Reparto de Volumen (kg)"), use_container_width=True)

    with tabs[1]:
        st.markdown("### Análisis de Calidad y Liquidaciones")
        mask_s = df_seg_tir_raw['articulo'].astype(str).str.contains("II", case=False)
        df_seg = df_seg_tir_raw[mask_s]
        mask_t = df_seg_tir_raw['cliente'].astype(str).str.contains("tirado", case=False)
        df_tir = df_seg_tir_raw[mask_t]

        c1, c2, c3 = st.columns(3)
        c1.metric("Segundas (II)", f"{form(df_seg['pesonetovendido'].sum(), 0)} kg")
        c2.metric("Liquidado (Tirado)", f"{form(df_tir['pesonetovendido'].sum(), 0)} kg")
        impacto = ((df_seg['pesonetovendido'].sum() + df_tir['pesonetovendido'].sum()) / t_kg_v * 100)
        c3.metric("Impacto s/ Primera", f"{form(impacto, 2)} %")
        
        st.plotly_chart(px.area(df_seg_tir_raw[mask_s | mask_t].groupby('fecha_semana')['pesonetovendido'].sum().reset_index(), 
                                x='fecha_semana', y='pesonetovendido', title="Evolución Semanal de Mermas y Segundas"), use_container_width=True)

    with tabs[2]:
        st.markdown("### Gestión de Reclamaciones (RR)")
        t_vta_spec = df_special['venta_neta'].sum()
        st.metric("Pérdida por Reclamaciones", f"{form(t_vta_spec)} €", delta=f"{form(abs(t_vta_spec)/t_kg_v, 4)} €/kg de impacto")
        st.dataframe(df_special[['fecha_semana', 'familia', 'cliente', 'venta_neta']].sort_values('venta_neta'), use_container_width=True)

else:
    st.error("No se han encontrado los datos para la demo. Asegúrate de que 'datos_acl.xlsx' está en el repositorio.")

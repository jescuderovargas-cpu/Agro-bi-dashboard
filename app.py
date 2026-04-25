import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Demo BI - Gestión Agrícola", layout="wide")

# --- ESTILO ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #2E7D32 !important; font-size: 1.8rem !important; }
    h3 { color: #333333; background-color: #f8f9fa; padding: 8px; border-radius: 5px; font-size: 1rem !important; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
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
    # --- BARRA LATERAL CON TODOS LOS FILTROS ---
    st.sidebar.header("CONFIGURACIÓN")
    
    # Filtro Semanas
    op_sem = sorted(df_raw['fecha_semana'].unique())
    sel_sem = st.sidebar.multiselect("Semanas", op_sem, default=op_sem)
    
    # Filtro Familias
    op_fam = sorted(df_raw['familia'].unique())
    sel_fam = st.sidebar.multiselect("Familias", op_fam, default=op_fam)
    
    # Filtro Clientes
    op_cli = sorted(df_raw['cliente'].unique())
    sel_cli = st.sidebar.multiselect("Clientes", op_cli, default=op_cli)

    # --- APLICACIÓN DE FILTROS ---
    df_f = df_raw.copy()
    if sel_sem: df_f = df_f[df_f['fecha_semana'].isin(sel_sem)]
    if sel_fam: df_f = df_f[df_f['familia'].isin(sel_fam)]
    if sel_cli: df_f = df_f[df_f['cliente'].isin(sel_cli)]
    
    df_f['alb_str'] = df_f['alb'].astype(str)
    
    # Copia para Segundas y Tirado (Sin filtros de limpieza de calidad)
    df_seg_tir_raw = df_f.copy()
    
    # Limpieza para análisis de rentabilidad (Solo Primera Calidad)
    is_rr = df_f['alb_str'].str.contains("RR", case=False)
    df_clean = df_f[is_rr | ~df_f['articulo'].astype(str).str.contains("II", case=False)]
    df_clean = df_clean[~df_clean['cliente'].astype(str).str.contains("Tirado", case=False)]
    
    df_op = df_clean[~is_rr]
    df_special = df_clean[is_rr]

    # Cálculos principales
    t_kg_v = df_op['pesonetovendido'].sum()
    t_vta = df_op['venta_neta'].sum()
    t_com = df_op['importecompra'].sum()
    t_alm = df_op[['estruct', 'mano_obra', 'c_envase', 'c_palet', 'cbo']].sum().sum()
    t_ope = df_op[['comision', 'porte_orig', 'porte_dest']].sum().sum()
    beneficio_neto = t_vta - (t_com + t_alm + t_ope)

    # Nombres de pestañas sin símbolos
    tabs = st.tabs(["Resumen", "Segundas y tirado", "Reclamaciones"])

    with tabs[0]:
        st.markdown("### Rentabilidad Neta")
        m1, m2, m3 = st.columns(3)
        m1.metric("Kilos Vendidos", f"{form(t_kg_v, 0)} kg")
        m2.metric("Beneficio Neto", f"{form(beneficio_neto)} €")
        m3.metric("Margen / Kg", f"{form(beneficio_neto/t_kg_v, 4) if t_kg_v>0 else 0} €/kg")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.bar(df_op.groupby('familia')['venta_neta'].sum().reset_index(), 
                                   x='familia', y='venta_neta', title="Ventas por Familia"), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df_op, values='pesonetovendido', names='familia', hole=0.4, title="Reparto de KG"), use_container_width=True)

        # --- SECCIÓN DE TABLA DE DATOS ---
        st.markdown("---")
        with st.expander("VER DETALLE DE DATOS (TABLA)"):
            st.write("Datos filtrados actualmente utilizados para el resumen:")
            # Mostramos una tabla limpia con las columnas clave
            columnas_ver = ['fecha_semana', 'familia', 'cliente', 'articulo', 'pesonetovendido', 'venta_neta']
            st.dataframe(df_op[columnas_ver].style.format({"venta_neta": "{:.2f} €", "pesonetovendido": "{:.0f} kg"}), use_container_width=True)
            
            st.download_button(
                label="Descargar estos datos en CSV",
                data=df_op.to_csv(index=False).encode('utf-8'),
                file_name='datos_resumen.csv',
                mime='text/csv',
            )

    with tabs[1]:
        st.markdown("### Control de Calidad")
        mask_s = df_seg_tir_raw['articulo'].astype(str).str.contains("II", case=False)
        df_seg = df_seg_tir_raw[mask_s]
        mask_t = df_seg_tir_raw['cliente'].astype(str).str.contains("Tirado", case=False)
        df_tir = df_seg_tir_raw[mask_t]

        c1, c2 = st.columns(2)
        c1.metric("Kilos Segundas (II)", f"{form(df_seg['pesonetovendido'].sum(), 0)} kg")
        c2.metric("Kilos en Tirado", f"{form(df_tir['pesonetovendido'].sum(), 0)} kg")
        
        st.plotly_chart(px.bar(df_seg_tir_raw[mask_s | mask_t].groupby('familia')['pesonetovendido'].sum().reset_index(), 
                               x='familia', y='pesonetovendido', color='familia', title="Mermas por Familia"), use_container_width=True)

    with tabs[2]:
        st.markdown("### Reclamaciones y Abonos")
        t_vta_spec = df_special['venta_neta'].sum()
        st.metric("Pérdida Total", f"{form(t_vta_spec)} €")
        st.dataframe(df_special[['fecha_semana', 'familia', 'cliente', 'venta_neta']], use_container_width=True)

else:
    st.error("Por favor, sube el archivo 'datos_acl.xlsx' a GitHub para visualizar la demo.")

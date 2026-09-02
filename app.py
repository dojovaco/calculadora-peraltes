import streamlit as st
import pandas as pd
import numpy as np
import os

# Configuración de la página
st.set_page_config(page_title="Calculadora de Peraltes y Transiciones", layout="wide")

# Estilos CSS para mejorar la vista en teléfonos y pantallas pequeñas
st.markdown("""
    <style>
        @media (max-width: 768px) {
            h1 {
                font-size: 1.6rem !important;
            }
        }
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 8px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🛣️ Calculadora de Peraltes")
st.markdown("Normas AASHTO - Consulta y cálculo automático.")

# Función para cargar y limpiar los datos de Excel con detección automática de modificaciones
@st.cache_data
def cargar_datos(filepath='Peraltes.xlsx', mtime=None):
    xls = pd.ExcelFile(filepath)
    data = {}
    
    for e_max in [4, 6, 8]:
        # Cargar hoja de Peralte
        sheet_p = f'Peralte {e_max}%'
        df_p = pd.read_excel(xls, sheet_name=sheet_p, header=None)
        sub_p = df_p.iloc[2:].copy()
        sub_p.columns = ['Velocidad', 'Radio', 'Peralte']
        sub_p['Velocidad'] = pd.to_numeric(sub_p['Velocidad'], errors='coerce')
        sub_p['Radio'] = pd.to_numeric(sub_p['Radio'], errors='coerce')
        sub_p['Peralte_raw'] = sub_p['Peralte']
        sub_p['Peralte_num'] = pd.to_numeric(sub_p['Peralte'], errors='coerce')
        sub_p.dropna(subset=['Velocidad', 'Radio'], inplace=True)
        data[f'peralte_{e_max}'] = sub_p
        
        # Cargar hoja de Transición
        sheet_t = f'Transición de Peralte {e_max}%'
        df_t = pd.read_excel(xls, sheet_name=sheet_t, header=None)
        sub_t = df_t.iloc[1:].copy()
        sub_t.columns = ['Velocidad', 'Canales', 'Radio', 'Longitud_Transicion']
        sub_t['Velocidad'] = pd.to_numeric(sub_t['Velocidad'], errors='coerce')
        sub_t['Canales'] = pd.to_numeric(sub_t['Canales'], errors='coerce')
        sub_t['Radio'] = pd.to_numeric(sub_t['Radio'], errors='coerce')
        sub_t['Longitud_Transicion'] = pd.to_numeric(sub_t['Longitud_Transicion'], errors='coerce')
        sub_t.dropna(subset=['Velocidad', 'Radio', 'Canales'], inplace=True)
        data[f'transicion_{e_max}'] = sub_t
        
    return data

# Obtener la fecha de modificación del archivo para refrescar caché automáticamente
archivo_excel = 'Peraltes.xlsx'
mtime = os.path.getmtime(archivo_excel) if os.path.exists(archivo_excel) else None

try:
    datos_globales = cargar_datos(archivo_excel, mtime=mtime)
except Exception as e:
    st.error(f"Error al cargar el archivo Peraltes.xlsx: {e}")
    st.stop()

# Función auxiliar para convertir el valor decimal a porcentaje limpio
def convertir_a_porcentaje(val):
    if pd.isna(val):
        return "-"
    val_str = str(val).strip()
    try:
        num = float(val_str)
        return f"{num * 100:.1f}%"
    except ValueError:
        return val_str

# Función para formatear progresivas en formato 0+000,00
def formatear_progresiva(val):
    if pd.isna(val) or not isinstance(val, (int, float, np.number)):
        return "-"
    signo = "-" if val < 0 else ""
    val_abs = abs(val)
    km = int(val_abs // 1000)
    m = val_abs % 1000
    m_str = f"{m:06.2f}".replace('.', ',')
    return f"{signo}{km}+{m_str}"

# Barra lateral para parámetros de diseño
st.sidebar.header("Parámetros de Diseño")

e_max_op = st.sidebar.selectbox("Peralte Máximo ($e_{max}$)", [4, 6, 8], format_func=lambda x: f"{x}%")

key_p = f'peralte_{e_max_op}'
df_p_disp = datos_globales[key_p]

velocidades_disponibles = sorted(df_p_disp['Velocidad'].unique())
velocidad_op = st.sidebar.selectbox("Velocidad de Diseño (km/h)", velocidades_disponibles)

df_p_v = df_p_disp[df_p_disp['Velocidad'] == velocidad_op].sort_values(by='Radio')
radios_norma = df_p_v['Radio'].unique()

tipo_entrada_radio = st.sidebar.radio("Método de Radio", ["Seleccionar de la norma", "Ingresar valor manual"])

if tipo_entrada_radio == "Seleccionar de la norma":
    radio_op = st.sidebar.selectbox("Radio de Curvatura (m)", sorted(radios_norma, reverse=True))
else:
    min_r = float(radios_norma.min())
    max_r = float(radios_norma.max())
    radio_op = st.sidebar.number_input(
        f"Radio de Curvatura (m) [Rango: {min_r} - {max_r}]", 
        min_value=min_r, 
        max_value=max_r, 
        value=float(min_r),
        step=1.0
    )

canales_op = st.sidebar.selectbox("Canales de Circulación", [2, 4], index=0, key="select_canales_circulacion")

# Inputs de Progresivas de Diseño (en metros)
st.sidebar.subheader("Progresivas de Diseño")
prog_te = st.sidebar.number_input("Progresiva TE (Tangente de Entrada - m)", value=0.0, step=1.0, format="%.2f")
prog_ts = st.sidebar.number_input("Progresiva TS (Tangente de Salida - m)", value=100.0, step=1.0, format="%.2f")

distribucion_op = st.sidebar.selectbox(
    "Distribución de Transición (Tangente / Curva)",
    ["66.7% - 33.3%", "50% - 50%"],
    index=0
)

key_t = f'transicion_{e_max_op}'
df_t_v = datos_globales[key_t][
    (datos_globales[key_t]['Velocidad'] == velocidad_op) & 
    (datos_globales[key_t]['Canales'] == canales_op)
].drop_duplicates(subset=['Radio']).sort_values(by='Radio')

peralte_val_fmt = "No disponible"
long_trans = "No disponible"
tipo_resultado = "Exacto"

match_p = df_p_v[df_p_v['Radio'] == radio_op]

if not match_p.empty:
    raw_p = match_p['Peralte_raw'].values[0]
    peralte_val_fmt = convertir_a_porcentaje(raw_p)
    
    match_t = df_t_v[df_t_v['Radio'] == radio_op]
    if not match_t.empty:
        long_trans = match_t['Longitud_Transicion'].values[0]
else:
    df_num = df_p_v.dropna(subset=['Peralte_num'])
    
    if radio_op > df_num['Radio'].max() or radio_op < df_num['Radio'].min():
        radio_cercano = min(radios_norma, key=lambda x: abs(x - radio_op))
        match_p = df_p_v[df_p_v['Radio'] == radio_cercano]
        raw_p = match_p['Peralte_raw'].values[0]
        peralte_val_fmt = convertir_a_porcentaje(raw_p)
        
        match_t = df_t_v[df_t_v['Radio'] == radio_cercano]
        long_trans = match_t['Longitud_Transicion'].values[0] if not match_t.empty else "No disponible"
        tipo_resultado = f"Aproximado (Radio más cercano: {radio_cercano} m)"
    else:
        radios_num = df_num['Radio'].values
        r_inferior = max([r for r in radios_num if r <= radio_op], default=None)
        r_superior = min([r for r in radios_num if r >= radio_op], default=None)
        
        if r_inferior is not None and r_superior is not None:
            if r_inferior == r_superior:
                match_p = df_num[df_num['Radio'] == r_inferior]
                raw_p = match_p['Peralte_raw'].values[0]
                peralte_val_fmt = convertir_a_porcentaje(raw_p)
                
                match_t = df_t_v[df_t_v['Radio'] == r_inferior]
                long_trans = match_t['Longitud_Transicion'].values[0] if not match_t.empty else "No disponible"
            else:
                row_inf = df_num[df_num['Radio'] == r_inferior].iloc[0]
                row_sup = df_num[df_num['Radio'] == r_superior].iloc[0]
                
                e_inf = row_inf['Peralte_num']
                e_sup = row_sup['Peralte_num']
                
                e_interpolado = e_inf + (e_sup - e_inf) * (radio_op - r_inferior) / (r_superior - r_inferior)
                peralte_val_fmt = f"{e_interpolado * 100:.2f}% (Interpolado)"
                
                match_t_inf = df_t_v[df_t_v['Radio'] == r_inferior]
                match_t_sup = df_t_v[df_t_v['Radio'] == r_superior]
                
                if not match_t_inf.empty and not match_t_sup.empty:
                    lt_inf = match_t_inf['Longitud_Transicion'].values[0]
                    lt_sup = match_t_sup['Longitud_Transicion'].values[0]
                    lt_interpolado = lt_inf + (lt_sup - lt_inf) * (radio_op - r_inferior) / (r_superior - r_inferior)
                    long_trans = round(lt_interpolado, 2)
                
                tipo_resultado = "Interpolado linealmente"
        else:
            radio_cercano = min(radios_norma, key=lambda x: abs(x - radio_op))
            match_p = df_p_v[df_p_v['Radio'] == radio_cercano]
            raw_p = match_p['Peralte_raw'].values[0]
            peralte_val_fmt = convertir_a_porcentaje(raw_p)
            match_t = df_t_v[df_t_v['Radio'] == radio_cercano]
            long_trans = match_t['Longitud_Transicion'].values[0] if not match_t.empty else "No disponible"
            tipo_resultado = f"Aproximado (Radio más cercano: {radio_cercano} m)"

st.info(f"Modo de cálculo: **{tipo_resultado}**")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Peralte Calculado ($e$)", value=peralte_val_fmt)

with col2:
    trans_val = f"{long_trans} m" if isinstance(long_trans, (int, float, np.number)) else long_trans
    st.metric(label="Longitud de Transición ($L_t$)", value=trans_val)

with col3:
    st.metric(label="Radio Ingresado", value=f"{radio_op} m")

# Cálculo de Progresivas de Transición
pct_tangente = 0.667 if distribucion_op == "66.7% - 33.3%" else 0.500

if isinstance(long_trans, (int, float, np.number)):
    lt_en_tangente = long_trans * pct_tangente
    lt_en_curva = long_trans * (1 - pct_tangente)
    prog_comienza_trans = prog_te - lt_en_tangente
    prog_peralte_pleno = prog_te + lt_en_curva
else:
    prog_comienza_trans = 0
    prog_peralte_pleno = 0

st.subheader("📍 Progresivas Críticas de Transición (Entrada)")
col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    st.metric(label="Inicio de Transición", value=formatear_progresiva(prog_comienza_trans))
with col_p2:
    st.metric(label="Punto TE", value=formatear_progresiva(prog_te))
with col_p3:
    st.metric(label="Alcanza Peralte Pleno", value=formatear_progresiva(prog_peralte_pleno))

st.markdown("---")
st.subheader("Tabla de Referencia Normativa para la Velocidad Seleccionada")

df_tabla_mostrar = pd.merge(
    df_p_v[['Radio', 'Peralte_raw']].drop_duplicates(subset=['Radio']),
    df_t_v[['Radio', 'Longitud_Transicion']].drop_duplicates(subset=['Radio']),
    on='Radio',
    how='outer'
).sort_values(by='Radio', ascending=False).copy()

df_tabla_mostrar['Peralte'] = df_tabla_mostrar['Peralte_raw'].apply(convertir_a_porcentaje)
df_tabla_mostrar = df_tabla_mostrar[['Radio', 'Peralte', 'Longitud_Transicion']]
df_tabla_mostrar.columns = ['Radio (m)', 'Peralte / Condición', f'Longitud Transición ({canales_op} canales)']

st.dataframe(df_tabla_mostrar.reset_index(drop=True), use_container_width=True, hide_index=True)

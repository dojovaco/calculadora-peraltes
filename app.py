import streamlit as st
import pandas as pd
import numpy as np
import os

# Configuración de la página
st.set_page_config(page_title="Calculadora de Peraltes y Transiciones", layout="wide")

st.title("🛣️ Calculadora de Peraltes y Transiciones v1.0")
st.markdown("Herramienta basada en normas AASHTO para la consulta y cálculo automático por interpolación lineal.")

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
        sub_p['Peralte_raw'] = sub_p['Peralte'] # Guardar valor original
        sub_p['Peralte_num'] = pd.to_numeric(sub_p['Peralte'], errors='coerce') # Para interpolar si es numérico
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

# Barra lateral para parámetros de diseño
st.sidebar.header("Parámetros de Diseño")

if st.sidebar.button("🔄 Recargar datos de Excel"):
    st.cache_data.clear()
    st.rerun()

e_max_op = st.sidebar.selectbox("Peralte Máximo ($e_{max}$)", [4, 6, 8], format_func=lambda x: f"{x}%")

key_p = f'peralte_{e_max_op}'
df_p_disp = datos_globales[key_p]

# Seleccionar velocidad disponible para ese e_max
velocidades_disponibles = sorted(df_p_disp['Velocidad'].unique())
velocidad_op = st.sidebar.selectbox("Velocidad de Diseño (km/h)", velocidades_disponibles)

# Filtrar radios disponibles para la velocidad elegida
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

canales_op = st.sidebar.selectbox("Canales de Circulación", [2, 4], index=0)

canales_op = st.sidebar.selectbox("Canales de Circulación", [2, 4], index=0)

key_t = f'transicion_{e_max_op}'
df_t_v = datos_globales[key_t][
    (datos_globales[key_t]['Velocidad'] == velocidad_op) & 
    (datos_globales[key_t]['Canales'] == canales_op)
].drop_duplicates(subset=['Radio']).sort_values(by='Radio')

# Lógica de búsqueda exacta o interpolación lineal
peralte_val_fmt = "No disponible"
long_trans = "No disponible"
tipo_resultado = "Exacto"

# Verificar si el radio está exactamente en la tabla
match_p = df_p_v[df_p_v['Radio'] == radio_op]

if not match_p.empty:
    # Coincidencia exacta
    raw_p = match_p['Peralte_raw'].values[0]
    peralte_val_fmt = convertir_a_porcentaje(raw_p)
    
    match_t = df_t_v[df_t_v['Radio'] == radio_op]
    if not match_t.empty:
        long_trans = match_t['Longitud_Transicion'].values[0]
else:
    # Radio no tabulado -> Interpolación Lineal
    # Filtramos filas donde el peralte sea puramente numérico para poder interpolar
    df_num = df_p_v.dropna(subset=['Peralte_num'])
    
    if radio_op > df_num['Radio'].max() or radio_op < df_num['Radio'].min():
        # Fuera de rango numérico (puede estar en zona de NC/RC)
        # Tomamos el radio más cercano
        radio_cercano = min(radios_norma, key=lambda x: abs(x - radio_op))
        match_p = df_p_v[df_p_v['Radio'] == radio_cercano]
        raw_p = match_p['Peralte_raw'].values[0]
        peralte_val_fmt = convertir_a_porcentaje(raw_p)
        
        match_t = df_t_v[df_t_v['Radio'] == radio_cercano]
        long_trans = match_t['Longitud_Transicion'].values[0] if not match_t.empty else "No disponible"
        tipo_resultado = f"Aproximado (Radio más cercano: {radio_cercano} m)"
    else:
        # Encontramos los dos radios entre los cuales cae el radio ingresado
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
                # Datos inferior y superior para peralte
                row_inf = df_num[df_num['Radio'] == r_inferior].iloc[0]
                row_sup = df_num[df_num['Radio'] == r_superior].iloc[0]
                
                e_inf = row_inf['Peralte_num']
                e_sup = row_sup['Peralte_num']
                
                # Interpolación lineal de peralte
                # A menor radio, mayor peralte (relación inversa en tablas AASHTO)
                e_interpolado = e_inf + (e_sup - e_inf) * (radio_op - r_inferior) / (r_superior - r_inferior)
                peralte_val_fmt = f"{e_interpolado * 100:.2f}% (Interpolado)"
                
                # Interpolación lineal de longitud de transición
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

# Mostrar resultados en pantalla principal
st.info(f"Modo de cálculo: **{tipo_resultado}**")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Peralte Calculado ($e$)", value=peralte_val_fmt)

with col2:
    st.metric(label="Longitud de Transición ($L_t$)", value=f"{long_trans} m" if isinstance(long_trans, (int, float, np.number)) else long_trans)

with col3:
    st.metric(label="Radio Ingresado", value=f"{radio_op} m")

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

st.dataframe(df_tabla_mostrar.reset_index(drop=True), use_container_width=True)

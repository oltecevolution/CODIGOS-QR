import streamlit as st
import sqlite3
import json
import qrcode
import io
import os

# Configuración de la página
st.set_page_config(page_title="Enterprise QR System", page_icon="🔍", layout="冷静")

DB_FILE = "qr_streamlit.db"

# --- FUNCIONES DE BASE DE DATOS (SQLite nativo para Streamlit) ---
def conectar_db():
    conn = sqlite3.connect(DB_FILE)
    return conn

def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qritems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            fecha TEXT,
            logo_bytes BLOB,
            imagen_bytes BLOB,
            tabla_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

crear_tablas()

# --- DETECTAR SI ES UN ESCANEO DE QR O EL PANEL ADMINISTRADOR ---
# Si la URL tiene un formato como: app.streamlit.app/?id=1
query_params = st.query_params

if "id" in query_params:
    # --- VISTA DEL CELULAR (AL ESCANEAR EL QR) ---
    item_id = query_params["id"]
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, descripcion, fecha, logo_bytes, imagen_bytes, tabla_json FROM qritems WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        titulo, descripcion, fecha, logo_bytes, imagen_bytes, tabla_json = row
        tabla_datos = json.loads(tabla_json)
        
        # Diseño de la Ficha Técnica
        col_tit, col_logo = st.columns([3, 1])
        with col_tit:
            st.title(titulo)
            st.caption(f"📅 Fecha de Referencia: {fecha}")
        with col_logo:
            if logo_bytes:
                st.image(logo_bytes, width=100)
                
        if descripcion:
            st.info(descripcion)
            
        st.subheader("📋 Especificaciones Técnicas")
        # Mostrar tabla estilizada
        st.table(tabla_datos)
        
        if imagen_bytes:
            st.subheader("🖼️ Registro Visual")
            st.image(imagen_bytes, use_container_width=True)
    else:
        st.error("Error 404: El activo solicitado no existe.")

else:
    # --- PANEL DE CONTROL ADMINISTRADOR ---
    st.title("🎛️ Panel de Control QR Asset Manager")
    
    tab1, tab2 = st.tabs(["🆕 Crear Activo", "📦 Ver Inventario"])
    
    with tab1:
        st.header("Crear Nuevo Activo QR")
        with st.form("form_crear", clear_on_submit=True):
            titulo = st.text_input("Título del Activo", placeholder="Ej. Generador Eléctrico")
            fecha = st.date_input("Fecha de Referencia")
            descripcion = st.text_area("Descripción General")
            
            logo_file = st.file_uploader("Subir Logo Corporativo", type=["png", "jpg", "jpeg"])
            imagen_file = st.file_uploader("Subir Imagen del Activo", type=["png", "jpg", "jpeg"])
            
            st.write("---")
            st.subheader("Tabla de Datos Dinámica (Formato Llave: Valor)")
            st.caption("Escribe las propiedades separadas por comas. Ej: Voltaje:220V, Marca:Siemens")
            tabla_input = st.text_input("Propiedades", placeholder="Voltaje:220V, Marca:Siemens, Estado:Operativo")
            
            boton_guardar = st.form_submit_button("Guardar Activo")
            
            if boton_guardar and titulo:
                # Procesar Tabla JSON
                diccionario_tabla = {}
                if tabla_input:
                    items = tabla_input.split(",")
                    for i in items:
                        if ":" in i:
                            k, v = i.split(":", 1)
                            diccionario_tabla[k.strip()] = v.strip()
                
                # Procesar Archivos a Bytes
                logo_bytes = logo_file.read() if logo_file else None
                img_bytes = imagen_file.read() if imagen_file else None
                
                # Guardar en BD
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO qritems (titulo, descripcion, fecha, logo_bytes, imagen_bytes, tabla_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (titulo, descripcion, str(fecha), logo_bytes, img_bytes, json.dumps(diccionario_tabla)))
                conn.commit()
                conn.close()
                st.success(f"¡Activo '{titulo}' creado con éxito! Ve al inventario para obtener tu QR.")
                
    with tab2:
        st.header("Activos Registrados")
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo, fecha FROM qritems")
        activos = cursor.fetchall()
        conn.close()
        
        for act in activos:
            id_act, tit_act, fec_act = act
            with st.expander(f"📦 #{id_act} - {tit_act} ({fec_act})"):
                # Aquí generaríamos la URL real una vez publicado, por ahora simula localhost
                # En producción reemplaza esto por la URL que te dé Streamlit Share
                url_base = "https://tu-app.streamlit.app" 
                url_destino = f"{url_base}/?id={id_act}"
                
                st.write(f"**Enlace del QR:** `{url_destino}`")
                
                # Generar QR en memoria
                qr = qrcode.make(url_destino)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.image(byte_im, width=200, caption="Código QR para imprimir")
                st.download_button(label="📥 Descargar Código QR", data=byte_im, file_name=f"QR_{id_act}.png", mime="image/png")
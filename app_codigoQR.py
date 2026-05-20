import streamlit as st
import sqlite3
import json
import qrcode
import io
import os

# Configuración de la página
st.set_page_config(page_title="Enterprise QR System", page_icon="🔍", layout="wide")

DB_FILE = "qr_streamlit.db"

# --- FUNCIONES DE BASE DE DATOS ---
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
        
        col_tit, col_logo = st.columns([3, 1])
        with col_tit:
            st.title(titulo)
            st.caption(f"📅 Última Actualización / F. Ref: {fecha}")
        with col_logo:
            if logo_bytes:
                st.image(logo_bytes, width=100)
                
        if descripcion:
            st.info(descripcion)
            
        st.subheader("📋 Especificaciones Técnicas")
        st.table(tabla_datos)
        
        if imagen_bytes:
            st.subheader("🖼️ Registro Visual")
            st.image(imagen_bytes, use_container_width=True)
    else:
        st.error("Error 404: El activo solicitado no existe.")

else:
    # --- PANEL DE CONTROL ADMINISTRADOR ---
    st.title("🎛️ Panel de Control QR Asset Manager")
    
    tab1, tab2 = st.tabs(["🆕 Crear Activo", "📦 Ver e Invetario / Editar"])
    
    with tab1:
        st.header("Crear Nuevo Activo QR")
        with st.form("form_crear", clear_on_submit=True):
            titulo = st.text_input("Título del Activo", placeholder="Ej. Generador Eléctrico")
            fecha = st.date_input("Fecha de Referencia")
            descripcion = st.text_area("Descripción General")
            
            logo_file = st.file_uploader("Subir Logo Corporativo", type=["png", "jpg", "jpeg"], key="logo_crear")
            imagen_file = st.file_uploader("Subir Imagen del Activo", type=["png", "jpg", "jpeg"], key="img_crear")
            
            st.write("---")
            st.subheader("Tabla de Datos Dinámica (Formato Llave: Valor)")
            st.caption("Escribe las propiedades separadas por comas. Ej: Voltaje:220V, Marca:Siemens")
            tabla_input = st.text_input("Propiedades", placeholder="Voltaje:220V, Marca:Siemens, Estado:Operativo")
            
            boton_guardar = st.form_submit_button("Guardar Activo")
            
            if boton_guardar and titulo:
                diccionario_tabla = {}
                if tabla_input:
                    items = tabla_input.split(",")
                    for i in items:
                        if ":" in i:
                            k, v = i.split(":", 1)
                            diccionario_tabla[k.strip()] = v.strip()
                
                logo_bytes = logo_file.read() if logo_file else None
                img_bytes = imagen_file.read() if imagen_file else None
                
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO qritems (titulo, descripcion, fecha, logo_bytes, imagen_bytes, tabla_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (titulo, descripcion, str(fecha), logo_bytes, img_bytes, json.dumps(diccionario_tabla)))
                conn.commit()
                conn.close()
                st.success(f"¡Activo '{titulo}' creado con éxito!")
                st.rerun()
                
    with tab2:
        st.header("Activos Registrados e Historial")
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo, fecha, descripcion, tabla_json FROM qritems")
        activos = cursor.fetchall()
        conn.close()
        
        for act in activos:
            id_act, tit_act, fec_act, desc_act, json_act = act
            
            with st.expander(f"📦 #{id_act} - {tit_act} (Último cambio: {fec_act})"):
                
                # REEMPLAZA ESTO CON TU URL REAL DE STREAMLIT
                url_base = "https://appcodigoqrpy-qq6t4cdkwkunwgqtxywuez.streamlit.app" 
                url_destino = f"{url_base}/?id={id_act}"
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("Visualización y Descarga del QR")
                    st.write(f"**Enlace permanente:** `{url_destino}`")
                    
                    # Generar código QR
                    qr = qrcode.make(url_destino)
                    buf = io.BytesIO()
                    qr.save(buf, format="PNG")
                    byte_im = buf.getvalue()
                    
                    st.image(byte_im, width=180)
                    st.download_button(label="📥 Descargar Código QR", data=byte_im, file_name=f"QR_{id_act}.png", mime="image/png", key=f"dl_{id_act}")
                
                with col2:
                    st.subheader(f"📝 Editar Información de #{id_act}")
                    
                    # Formulario de edición periódica
                    with st.form(f"form_editar_{id_act}"):
                        nuevo_titulo = st.text_input("Editar Título", value=tit_act)
                        nueva_fecha = st.text_input("Fecha de Actualización (AAAA-MM-DD)", value=fec_act)
                        nueva_desc = st.text_area("Editar Descripción", value=desc_act)
                        
                        # Convertir el JSON de vuelta a texto plano para que el usuario pueda editarlo fácil
                        datos_dicc = json.loads(json_act)
                        texto_tabla_actual = ", ".join([f"{k}:{v}" for k, v in datos_dicc.items()])
                        nueva_tabla_input = st.text_input("Modificar Tabla de Datos", value=texto_tabla_actual)
                        
                        st.caption("Archivos actuales preservados. Si subes uno nuevo, se reemplazará:")
                        nuevo_logo_file = st.file_uploader("Reemplazar Logo", type=["png", "jpg", "jpeg"], key=f"logo_edit_{id_act}")
                        nuevo_img_file = st.file_uploader("Reemplazar Imagen", type=["png", "jpg", "jpeg"], key=f"img_edit_{id_act}")
                        
                        boton_actualizar = st.form_submit_button("💾 Guardar Cambios")
                        
                        if boton_actualizar:
                            # Procesar la nueva tabla
                            nuevo_dicc = {}
                            if nueva_tabla_input:
                                items_nuevos = nueva_tabla_input.split(",")
                                for i in items_nuevos:
                                    if ":" in i:
                                        k, v = i.split(":", 1)
                                        nuevo_dicc[k.strip()] = v.strip()
                            
                            conn = conectar_db()
                            cursor = conn.cursor()
                            
                            # Actualizar texto y datos básicos
                            cursor.execute('''
                                UPDATE qritems 
                                SET titulo = ?, fecha = ?, descripcion = ?, tabla_json = ? 
                                WHERE id = ?
                            ''', (nuevo_titulo, nueva_fecha, nueva_desc, json.dumps(nuevo_dicc), id_act))
                            
                            # Si subió un logo nuevo, actualizarlo en la celda BLOB
                            if nuevo_logo_file:
                                cursor.execute("UPDATE qritems SET logo_bytes = ? WHERE id = ?", (nuevo_logo_file.read(), id_act))
                            
                            # Si subió una imagen nueva, actualizarla en la celda BLOB
                            if nuevo_img_file:
                                cursor.execute("UPDATE qritems SET imagen_bytes = ? WHERE id = ?", (nuevo_img_file.read(), id_act))
                                
                            conn.commit()
                            conn.close()
                            
                            st.success("¡Información actualizada periódicamente con éxito!")
                            st.rerun()
                            # --- BOTÓN DE ELIMINACIÓN ---
                    st.write("---")
                    # Usamos un expander para evitar que el usuario lo borre por accidente
                    with st.expander("⚠️ Zona de Peligro (Eliminar Activo)"):
                        st.warning("Esta acción es irreversible. Se borrarán todos los datos y fotos asociados.")
                        boton_eliminar = st.button(f"🚨 Confirmar Eliminación de #{id_act}", key=f"btn_del_{id_act}")
                        
                        if boton_eliminar:
                            conn = conectar_db()
                            cursor = conn.cursor()
                            # Borramos el registro de la tabla usando su ID único
                            cursor.execute("DELETE FROM qritems WHERE id = ?", (id_act,))
                            conn.commit()
                            conn.close()
                            
                            st.error(f"El activo #{id_act} ha sido eliminado del sistema.")
                            st.rerun()

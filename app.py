import streamlit as st
from config.conexion import obtener_conexion
import hashlib

st.set_page_config(
    page_title="Servi-Diagnóstico",
    page_icon="🧪",
    layout="centered"
)

# Título del sistema
st.title("SERVI-DIAGNÓSTICO")
st.subheader("Sistema de Gestión de la Información")
st.write("Bienvenido al sistema del laboratorio clínico")

st.divider()

# Formulario de inicio de sesión
st.subheader("Iniciar sesión")

with st.form("formulario_login"):
    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")
    ingresar = st.form_submit_button("Ingresar")

if ingresar:

    if not usuario or not contrasena:
        st.warning("Por favor, ingrese usuario y contraseña.")

    else:
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            contrasena_hash = hashlib.sha256(
                contrasena.encode()
            ).hexdigest()

            consulta = """
                SELECT
                    U.ID_User,
                    U.Nombre,
                    U.Apellido,
                    U.Usuario,
                    R.Nombre AS Rol
                FROM Usuario_Sistema U
                INNER JOIN Rol R
                    ON U.ID_Rol = R.ID_Rol
                WHERE U.Usuario = %s
                AND U.Contrasena = %s
                AND U.Estado = 'Activo'
            """

            cursor.execute(
                consulta,
                (usuario, contrasena_hash)
            )

            resultado = cursor.fetchone()

            if resultado:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = resultado
                st.success("¡Inicio de sesión exitoso!")
                st.rerun()

            else:
                st.error("Usuario o contraseña incorrectos.")

            cursor.close()
            conexion.close()

        except Exception as e:
            st.error("Error al conectar con la base de datos.")
            st.error(str(e))

# Pantalla después de iniciar sesión
if st.session_state.get("autenticado", False):

    datos = st.session_state["usuario"]

    st.success(
        f"Bienvenido, {datos['Nombre']} {datos['Apellido']}"
    )

    st.write(f"Rol: {datos['Rol']}")

    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

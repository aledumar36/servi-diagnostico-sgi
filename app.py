import streamlit as st
from config.conexion import obtener_conexion

st.set_page_config(
    page_title="Servi-Diagnóstico",
    page_icon="🧪",
    layout="wide"
)

st.title("Servi-Diagnóstico")
st.subheader("Sistema de Gestión de Información")

st.write("Bienvenido al sistema del laboratorio clínico.")

st.divider()

st.header("Prueba de conexión a la base de datos")

conexion = obtener_conexion()

if conexion is not None:
    try:
        if conexion.is_connected():
            st.success("¡Conexión exitosa con Clever Cloud!")
            cursor = conexion.cursor()
            cursor.execute("SELECT DATABASE()")
            base_datos = cursor.fetchone()

            st.write("Base de datos conectada:", base_datos[0])

            cursor.close()

        else:
            st.error("No se pudo establecer la conexión.")

    except Exception as error:
        st.error(f"Error durante la prueba: {error}")

    finally:
        conexion.close()

else:
    st.error("No fue posible conectar con la base de datos.")

import streamlit as st
import hashlib
from config.conexion import obtener_conexion
from modulos.PACIENTES import mostrar_pacientes

st.set_page_config(
    page_title="Servi-Diagnóstico",
    page_icon="🧪",
    layout="wide"
)

# ==========================================
# FUNCION: INICIO DE SESION
# ==========================================

def iniciar_sesion(usuario, contrasena):

    conexion = None
    cursor = None

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

        return resultado

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


# ==========================================
# PANTALLA DE INICIO DE SESION
# ==========================================

if not st.session_state.get("autenticado", False):

    st.title("SERVI-DIAGNÓSTICO")
    st.subheader("Sistema de Gestión de la Información")
    st.write("Bienvenido al sistema del laboratorio clínico")

    st.divider()

    st.subheader("Iniciar sesión")

    with st.form("formulario_login"):

        usuario = st.text_input("Usuario")

        contrasena = st.text_input(
            "Contraseña",
            type="password"
        )

        ingresar = st.form_submit_button(
            "Ingresar",
            use_container_width=True
        )

    if ingresar:

        if not usuario or not contrasena:
            st.warning("Ingrese su usuario y contraseña.")

        else:
            try:
                resultado = iniciar_sesion(
                    usuario,
                    contrasena
                )

                if resultado:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = resultado

                    st.rerun()

                else:
                    st.error("Usuario o contraseña incorrectos.")

            except Exception as e:
                st.error("No se pudo iniciar sesión.")
                st.error(str(e))


# ==========================================
# PANEL PRINCIPAL
# ==========================================

else:

    datos = st.session_state["usuario"]

    nombre_completo = (
        datos["Nombre"] + " " + datos["Apellido"]
    )

    rol = datos["Rol"]

    # --------------------------------------
    # MENU DEL REGENTE ADMINISTRADOR
    # --------------------------------------

    if rol.lower() == "regente-administrador":

        st.sidebar.title("SERVI-DIAGNÓSTICO")
        st.sidebar.caption("Panel administrativo")

        st.sidebar.write(
            f"Usuario: {nombre_completo}"
        )

        st.sidebar.write(
            f"Rol: {rol}"
        )

        st.sidebar.divider()

        opciones = [
            "Inicio",
            "Pacientes",
            "Citas",
            "Boletas de examen",
            "Registrar exámenes",
            "Exámenes por confirmar",
            "Consultar resultados",
            "Inventario",
            "Compras y proveedores",
            "Reseñas",
            "Usuarios y roles"
        ]

        seleccion = st.sidebar.radio(
            "MENÚ PRINCIPAL",
            opciones
        )

        st.sidebar.divider()

        if st.sidebar.button(
            "Cerrar sesión",
            use_container_width=True
        ):
            st.session_state.clear()
            st.rerun()

        # ----------------------------------
        # VISTA DE INICIO
        # ----------------------------------

        st.title("Panel principal")
        st.write(f"Bienvenido, {nombre_completo}")

        if seleccion == "Inicio":

            st.subheader("Resumen del laboratorio")

            st.write(
                "Desde este panel puede acceder a los "
                "diferentes módulos de Servi-Diagnóstico."
            )

            st.info(
                "Seleccione una opción del menú lateral "
                "para comenzar."
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🧪 Gestión de laboratorio")
                st.write(
                    "- Pacientes\n"
                    "- Citas\n"
                    "- Boletas de examen\n"
                    "- Registro de exámenes\n"
                    "- Validación de resultados\n"
                    "- Consulta de resultados"
                )

            with col2:
                st.markdown("### 📦 Administración")
                st.write(
                    "- Inventario\n"
                    "- Compras y proveedores\n"
                    "- Reseñas\n"
                    "- Usuarios y roles"
                )

        # ----------------------------------
        # VISTAS DE LOS MODULOS
        # ----------------------------------

       elif seleccion == "Pacientes":

    mostrar_pacientes()

        elif seleccion == "Citas":

            st.title("Gestión de citas")
            st.write("Administración de citas del laboratorio.")

        elif seleccion == "Boletas de examen":

            st.title("Boletas de examen")
            st.write("Registro de solicitudes de exámenes.")

        elif seleccion == "Registrar exámenes":

            st.title("Registro de exámenes")
            st.write("Ingreso de resultados de laboratorio.")

        elif seleccion == "Exámenes por confirmar":

            st.title("Exámenes por confirmar")
            st.write("Revisión y validación de resultados pendientes.")

        elif seleccion == "Consultar resultados":

            st.title("Consulta de resultados")
            st.write("Búsqueda de resultados de exámenes validados.")

        elif seleccion == "Inventario":

            st.title("Gestión de inventario")
            st.write("Control de productos, existencias y vencimientos.")

        elif seleccion == "Compras y proveedores":

            st.title("Compras y proveedores")
            st.write("Gestión de proveedores y órdenes de compra.")

        elif seleccion == "Reseñas":

            st.title("Reseñas de pacientes")
            st.write("Consulta de opiniones y calificaciones.")

        elif seleccion == "Usuarios y roles":

            st.title("Gestión de usuarios y roles")
            st.write("Administración de cuentas y permisos.")

        # Aviso de que las pantallas aún están en construcción
      if seleccion not in ["Inicio", "Pacientes"]:
    st.divider()
    st.info(
        "Esta sección está creada. "
        "El siguiente paso será desarrollar sus "
        "formularios y conectarlos con la base de datos."
    )

    else:

        st.title("SERVI-DIAGNÓSTICO")
        st.success(f"Bienvenido, {nombre_completo}")
        st.write(f"Rol: {rol}")

        st.info(
            "El menú correspondiente a este rol "
            "se configurará en la siguiente etapa."
        )

        if st.button("Cerrar sesión"):
            st.session_state.clear()
            st.rerun()

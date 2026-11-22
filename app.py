import streamlit as st
from modulos.SEGURIDAD import crear_hash, verificar_contrasena

from config.conexion import obtener_conexion
from modulos.PACIENTES import mostrar_pacientes
from modulos.CITAS import mostrar_citas
from modulos.BOLETAS import mostrar_boletas
from modulos.RESULTADOS import mostrar_resultados
from modulos.EXPEDIENTES import mostrar_expedientes
from modulos.INVENTARIO import mostrar_inventario
from modulos.PROVEEDORES import mostrar_proveedores
from modulos.USUARIOS import mostrar_usuarios
from modulos.PORTAL_PACIENTE import mostrar_portal_paciente

# ==========================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ==========================================

st.set_page_config(
    page_title="Servi-Diagnóstico",
    page_icon="🧪",
    layout="wide"
)


# ==========================================
# FUNCIÓN: INICIO DE SESIÓN
# ==========================================

def iniciar_sesion(usuario, contrasena):

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT U.ID_User, U.ID_Medico, U.ID_Paciente, U.Nombre,
                   U.Apellido, U.Usuario, U.Contrasena, R.Nombre AS Rol
            FROM Usuario_Sistema U
            INNER JOIN Rol R ON U.ID_Rol = R.ID_Rol
            WHERE U.Usuario = %s AND U.Estado = 'Activo'
        """, (usuario,))
        resultado = cursor.fetchone()
        if not resultado:
            return None
        valido, migrar = verificar_contrasena(contrasena, resultado['Contrasena'])
        if not valido:
            return None
        if migrar:
            cursor.execute(
                "UPDATE Usuario_Sistema SET Contrasena=%s WHERE ID_User=%s AND Contrasena=%s",
                (crear_hash(contrasena), resultado['ID_User'], resultado['Contrasena'])
            )
            conexion.commit()
        resultado.pop('Contrasena', None)
        return resultado

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


# ==========================================
# PANTALLA DE INICIO DE SESIÓN
# ==========================================

if not st.session_state.get("autenticado", False):

    st.title("SERVI-DIAGNÓSTICO")
    st.subheader("Sistema de Gestión de la Información")

    st.write(
        "Bienvenido al sistema del laboratorio clínico"
    )

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

            st.warning(
                "Ingrese su usuario y contraseña."
            )

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

                    st.error(
                        "Usuario o contraseña incorrectos."
                    )

            except Exception:

                st.error(
                    "No se pudo iniciar sesión. "
                    "Verifique la conexión e "
                    "inténtelo nuevamente."
                )


# ==========================================
# PANEL PRINCIPAL
# ==========================================

else:

    datos = st.session_state["usuario"]

    nombre_completo = (
        datos["Nombre"] + " " + datos["Apellido"]
    )

    rol = datos["Rol"]
    rol_normalizado = rol.strip().lower()

    # --------------------------------------
    # PERMISOS DEL MENÚ
    # --------------------------------------

    if rol_normalizado == "regente-administrador":

        opciones = [
            "Inicio",
            "Pacientes",
            "Citas",
            "Boletas de examen",
            "Resultados de exámenes",
            "Inventario",
            "Compras y proveedores",
            "Reseñas",
            "Usuarios y roles"
        ]

        descripcion_panel = "Panel administrativo"

    elif rol_normalizado == "secretario":

        opciones = [
            "Inicio",
            "Pacientes",
            "Citas",
            "Boletas de examen",
            "Resultados de exámenes"
        ]

        descripcion_panel = "Panel de secretaría"

    elif rol_normalizado in ["médico", "medico"]:

        opciones = ["Atención médica"]

        descripcion_panel = "Panel médico"

    elif rol_normalizado == "paciente":

        opciones = [
            "Mi portal"
        ]

        descripcion_panel = "Panel del paciente"

    else:

        st.error(
            "El rol de este usuario no tiene "
            "un menú configurado."
        )

        st.stop()

    # --------------------------------------
    # MENÚ LATERAL
    # --------------------------------------

    st.sidebar.title("SERVI-DIAGNÓSTICO")

    st.sidebar.caption(
        descripcion_panel
    )

    st.sidebar.write(
        f"Usuario: {nombre_completo}"
    )

    st.sidebar.write(
        f"Rol: {rol}"
    )

    st.sidebar.divider()

    if rol_normalizado in ["médico", "medico"]:
        # El médico entra directamente a su módulo, sin selector de Inicio.
        seleccion = "Atención médica"
    else:
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

    # --------------------------------------
    # VISTAS DE LOS MÓDULOS
    # --------------------------------------

    if seleccion == "Mi portal":

        mostrar_portal_paciente()

    elif seleccion == "Inicio":

        st.title("Panel principal")

        st.write(
            f"Bienvenido, {nombre_completo}"
        )

        st.subheader(
            "Resumen del laboratorio"
        )

        st.write(
            "Desde este panel puede acceder "
            "a los módulos disponibles de "
            "Servi-Diagnóstico."
        )

        if rol_normalizado in [
            "regente-administrador",
            "secretario"
        ]:

            st.markdown(
                "### 🧪 Gestión de laboratorio"
            )

            st.write(
                "- Registro y consulta de pacientes\n"
                "- Gestión de citas\n"
                "- Registro de boletas de examen\n"
                "- Carga y consulta de resultados\n"
                "- Seguimiento de exámenes pendientes"
            )

            if rol_normalizado == "regente-administrador":

                st.markdown(
                    "### 📦 Administración"
                )

                st.write(
                    "- Inventario\n"
                    "- Compras y proveedores\n"
                    "- Reseñas\n"
                    "- Usuarios y roles"
                )

        elif rol_normalizado in ["médico", "medico"]:

            st.markdown(
                "### 🩺 Atención médica"
            )

            st.write(
                "- Consulta de citas asignadas\n"
                "- Consulta de pacientes vinculados\n"
                "- Registro y consulta de expedientes médicos"
            )

            st.info(
                "Selecciona 'Atención médica' "
                "en el menú lateral para consultar "
                "tus asignaciones."
            )

        elif rol_normalizado == "paciente":

            st.markdown(
                "### 👤 Portal del paciente"
            )

            st.info(
                "Las funciones de consulta de "
                "citas y resultados personales "
                "se incorporarán posteriormente."
            )

    elif seleccion == "Pacientes":

        if rol_normalizado in [
            "regente-administrador",
            "secretario"
        ]:

            mostrar_pacientes()

        else:

            st.error(
                "No tienes permiso para acceder "
                "a este módulo."
            )

    elif seleccion == "Citas":

        if rol_normalizado in [
            "regente-administrador",
            "secretario"
        ]:

            mostrar_citas()

        else:

            st.error(
                "No tienes permiso para acceder "
                "a este módulo."
            )

    elif seleccion == "Boletas de examen":

        if rol_normalizado in [
            "regente-administrador",
            "secretario"
        ]:

            mostrar_boletas()

        else:

            st.error(
                "No tienes permiso para acceder "
                "a este módulo."
            )

    elif seleccion == "Resultados de exámenes":

        if rol_normalizado in [
            "regente-administrador",
            "secretario"
        ]:

            mostrar_resultados()

        else:

            st.error(
                "No tienes permiso para acceder "
                "a este módulo."
            )

    elif seleccion == "Atención médica":

        if rol_normalizado in ["médico", "medico"]:
            mostrar_expedientes()
        else:
            st.error("No tienes permiso para acceder a este módulo.")

    elif seleccion == "Inventario":
        if rol_normalizado == "regente-administrador":
            mostrar_inventario()


    elif seleccion == "Compras y proveedores":
        if rol_normalizado == "regente-administrador":
            mostrar_proveedores()


    elif seleccion == "Reseñas":

        if rol_normalizado == "regente-administrador":

            st.title(
                "Reseñas de pacientes"
            )

            st.write(
                "Consulta de opiniones "
                "y calificaciones."
            )

    elif seleccion == "Usuarios y roles":
        if rol_normalizado == "regente-administrador":
            mostrar_usuarios()
        else:
            st.error("No tienes permiso para acceder a este módulo.")

    # --------------------------------------
    # MÓDULOS PENDIENTES
    # --------------------------------------

    if seleccion in [
        "Reseñas"
    ]:

        st.divider()

        st.info(
            "Esta sección está creada. "
            "Sus formularios y conexión con "
            "la base de datos se desarrollarán "
            "posteriormente."
        )

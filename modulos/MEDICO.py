
import streamlit as st
from config.conexion import obtener_conexion


def mostrar_medico():

    st.title("🩺 Portal del médico")

    usuario = st.session_state.get("usuario", {})

    if not isinstance(usuario, dict):
        st.error("No se pudo identificar al usuario.")
        return

    if str(usuario.get("Rol", "")).strip().lower() not in ["medico", "médico"]:
        st.error("No tienes permiso para acceder.")
        return

    id_user = usuario.get("ID_User")

    if not id_user:
        st.error("No se encontró el usuario autenticado.")
        return

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        # Obtener el médico vinculado a la cuenta.
        cursor.execute("""
            SELECT
                U.ID_Medico,
                M.Nombre,
                M.Apellido
            FROM Usuario_Sistema U
            INNER JOIN Medico M
                ON U.ID_Medico = M.ID_Medico
            WHERE U.ID_User = %s
              AND U.ID_Rol = 3
              AND U.Estado = 'Activo'
        """, (id_user,))

        medico = cursor.fetchone()

        if not medico:
            st.warning(
                "Tu cuenta todavía no está vinculada "
                "con un médico registrado."
            )
            return

        id_medico = medico["ID_Medico"]

        st.success(
            f"Bienvenido, Dr./Dra. "
            f"{medico['Nombre']} {medico['Apellido']}"
        )

        pestaña_citas, pestaña_pacientes = st.tabs(
            ["📅 Mis citas", "👥 Mis pacientes"]
        )

        with pestaña_citas:

            st.subheader("Citas asignadas")

            cursor.execute("""
                SELECT
                    C.ID_Cita,
                    P.Nombre_Completo AS Paciente,
                    C.Fecha_Cita,
                    C.Concepto
                FROM Cita C
                INNER JOIN Paciente P
                    ON C.ID_Paciente = P.ID_Paciente
                WHERE C.ID_Medico = %s
                ORDER BY C.Fecha_Cita DESC
            """, (id_medico,))

            citas = cursor.fetchall()

            if citas:
                st.dataframe(
                    citas,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "Todavía no tienes citas asignadas."
                )

        with pestaña_pacientes:

            st.subheader("Pacientes vinculados")

            cursor.execute("""
                SELECT DISTINCT
                    P.ID_Paciente,
                    P.Nombre_Completo
                FROM Paciente P
                INNER JOIN Cita C
                    ON P.ID_Paciente = C.ID_Paciente
                WHERE C.ID_Medico = %s
                ORDER BY P.Nombre_Completo
            """, (id_medico,))

            pacientes = cursor.fetchall()

            if pacientes:
                st.dataframe(
                    pacientes,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "Todavía no tienes pacientes vinculados."
                )

    except Exception:
        st.error(
            "No fue posible cargar la información "
            "del médico. Revisa la conexión y "
            "los nombres de las tablas."
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()

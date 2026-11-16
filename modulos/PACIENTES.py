import streamlit as st
from config.conexion import obtener_conexion


def mostrar_pacientes():

    st.title("👥 Gestión de pacientes")
    st.write("Registro y consulta de pacientes de Servi-Diagnóstico.")

    pestaña_registro, pestaña_consulta = st.tabs(
        ["Registrar paciente", "Consultar pacientes"]
    )

    with pestaña_registro:

        st.subheader("Registrar nuevo paciente")

        with st.form("formulario_paciente"):

            nombre = st.text_input("Nombre completo *")
            telefono = st.text_input("Teléfono *")
            fecha_nacimiento = st.date_input(
                "Fecha de nacimiento",
                format="DD/MM/YYYY"
            )

            genero = st.selectbox(
                "Género",
                ["No especificado", "Masculino", "Femenino"]
            )

            dui = st.text_input("DUI (opcional)")
            correo = st.text_input("Correo electrónico")
            direccion = st.text_area("Dirección")
            telefono_emergencia = st.text_input(
                "Teléfono de emergencia"
            )

            guardar = st.form_submit_button(
                "Guardar paciente",
                use_container_width=True
            )

        if guardar:

            if not nombre.strip() or not telefono.strip():
                st.warning("El nombre y el teléfono son obligatorios.")

            else:

                conexion = None
                cursor = None

                try:
                    conexion = obtener_conexion()
                    cursor = conexion.cursor()

                    consulta = """
                        INSERT INTO Paciente (
                            Nombre_Completo,
                            Telefono,
                            Fecha_Nacimiento,
                            Genero,
                            DUI,
                            Correo,
                            Direccion,
                            Telefono_Emergencia
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    valores = (
                        nombre.strip(),
                        telefono.strip(),
                        fecha_nacimiento,
                        genero,
                        dui.strip() or None,
                        correo.strip() or None,
                        direccion.strip() or None,
                        telefono_emergencia.strip() or None
                    )

                    cursor.execute(consulta, valores)
                    conexion.commit()

                    st.success("¡Paciente registrado correctamente!")

                except Exception as error:
                    st.error(
                        "No se pudo registrar el paciente. "
                        "Verificá que el DUI no esté registrado anteriormente."
                    )
                    st.error(str(error))

                finally:
                    if cursor:
                        cursor.close()
                    if conexion:
                        conexion.close()

    with pestaña_consulta:

        st.subheader("Pacientes registrados")

        conexion = None
        cursor = None

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    ID_Paciente,
                    Nombre_Completo,
                    Telefono,
                    Fecha_Nacimiento,
                    Genero,
                    DUI,
                    Correo
                FROM Paciente
                ORDER BY ID_Paciente DESC
            """)

            pacientes = cursor.fetchall()

            if pacientes:
                st.dataframe(
                    pacientes,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Todavía no hay pacientes registrados.")

        except Exception as error:
            st.error("No se pudieron consultar los pacientes.")
            st.error(str(error))

        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

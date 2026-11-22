import streamlit as st
from datetime import date, datetime
from config.conexion import obtener_conexion


def formatear_fecha_nacimiento(valor):
    """Devuelve la fecha de nacimiento en formato DD/MM/YYYY."""
    if valor is None:
        return "No registrada"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor)


def etiqueta_paciente(paciente):
    codigo = f"P-{int(paciente['ID_Paciente']):06d}"
    nacimiento = formatear_fecha_nacimiento(paciente.get('Fecha_Nacimiento'))
    return f"{codigo} | {paciente['Nombre_Completo']} | {nacimiento}"


def mostrar_citas():
    st.title("📅 Gestión de citas")
    st.write("Registro y consulta de citas de Servi-Diagnóstico.")

    pestaña_registro, pestaña_consulta = st.tabs(
        ["Registrar cita", "Consultar citas"]
    )

    # ======================================
    # REGISTRAR CITAS
    # ======================================
    with pestaña_registro:
        st.subheader("Registrar nueva cita")
        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT ID_Paciente, Nombre_Completo, Fecha_Nacimiento
                FROM Paciente
                ORDER BY Nombre_Completo, Fecha_Nacimiento, ID_Paciente
            """)
            pacientes = cursor.fetchall()

            cursor.execute("""
                SELECT id_medico, nombre, apellido, Tipo
                FROM Medico
                ORDER BY nombre, apellido
            """)
            medicos = cursor.fetchall()

            if not pacientes:
                st.warning("Primero debés registrar al menos un paciente.")
            elif not medicos:
                st.warning("Primero debés registrar al menos un médico.")
            else:
                with st.form("formulario_cita"):
                    paciente_seleccionado = st.selectbox(
                        "Seleccionar paciente *",
                        pacientes,
                        format_func=etiqueta_paciente
                    )
                    medico_seleccionado = st.selectbox(
                        "Seleccionar médico *",
                        medicos,
                        format_func=lambda m: (
                            f"{m['nombre']} {m['apellido']} ({m['Tipo']})"
                        )
                    )
                    concepto = st.text_area("Concepto de la cita *")
                    fecha_cita = st.date_input(
                        "Fecha de la cita",
                        min_value=date.today(),
                        value=date.today(),
                        format="DD/MM/YYYY"
                    )
                    hora_cita = st.time_input(
                        "Hora de la cita",
                        value=datetime.strptime("08:00", "%H:%M").time()
                    )
                    guardar = st.form_submit_button(
                        "Guardar cita", use_container_width=True
                    )

                if guardar:
                    if not concepto.strip():
                        st.warning("Debés ingresar el concepto de la cita.")
                    else:
                        try:
                            consulta = """
                                INSERT INTO Cita (
                                    ID_Paciente, ID_Medico, Concepto, Fecha_Cita
                                ) VALUES (%s, %s, %s, %s)
                            """
                            valores = (
                                paciente_seleccionado["ID_Paciente"],
                                medico_seleccionado["id_medico"],
                                concepto.strip(),
                                datetime.combine(fecha_cita, hora_cita)
                            )
                            cursor.execute(consulta, valores)
                            conexion.commit()
                            st.success("¡Cita registrada correctamente!")
                            st.info(f"Paciente: {etiqueta_paciente(paciente_seleccionado)}")
                        except Exception:
                            conexion.rollback()
                            raise
        except Exception as error:
            st.error("No se pudo procesar la cita.")
            st.error(str(error))
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    # ======================================
    # CONSULTAR CITAS
    # ======================================
    with pestaña_consulta:
        st.subheader("Citas registradas")
        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    C.ID_Cita,
                    P.ID_Paciente,
                    P.Nombre_Completo AS Paciente,
                    P.Fecha_Nacimiento,
                    CONCAT(M.nombre, ' ', M.apellido) AS Medico,
                    M.Tipo AS Tipo_Medico,
                    C.Concepto,
                    C.Fecha_Cita
                FROM Cita C
                INNER JOIN Paciente P ON C.ID_Paciente = P.ID_Paciente
                INNER JOIN Medico M ON C.ID_Medico = M.id_medico
                ORDER BY C.Fecha_Cita DESC
            """)
            citas = cursor.fetchall()
            if citas:
                datos = []
                for cita in citas:
                    datos.append({
                        "ID_Cita": cita["ID_Cita"],
                        "Código paciente": f"P-{int(cita['ID_Paciente']):06d}",
                        "Paciente": cita["Paciente"],
                        "Fecha de nacimiento": formatear_fecha_nacimiento(
                            cita["Fecha_Nacimiento"]
                        ),
                        "Médico": cita["Medico"],
                        "Tipo de médico": cita["Tipo_Medico"],
                        "Concepto": cita["Concepto"],
                        "Fecha de cita": cita["Fecha_Cita"]
                    })
                st.dataframe(datos, use_container_width=True, hide_index=True)
            else:
                st.info("Todavía no hay citas registradas.")
        except Exception as error:
            st.error("No se pudieron consultar las citas.")
            st.error(str(error))
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

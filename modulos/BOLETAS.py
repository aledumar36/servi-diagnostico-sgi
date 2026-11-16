import streamlit as st
from config.conexion import obtener_conexion


def consultar_datos(consulta, parametros=()):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute(consulta, parametros)
        resultados = cursor.fetchall()
        return resultados
    finally:
        cursor.close()
        conexion.close()


def mostrar_boletas():

    st.title("📋 Gestión de boletas de examen")
    st.write("Registro y consulta de boletas de Servi-Diagnóstico.")

    pestaña_registro, pestaña_consulta = st.tabs(
        ["📝 Registrar boleta", "🔎 Consultar boletas"]
    )

    # ==========================================
    # PESTAÑA 1: REGISTRAR BOLETA
    # ==========================================

    with pestaña_registro:

        st.subheader("Registro de nueva boleta")

        pacientes = consultar_datos("""
            SELECT ID_Paciente, Nombre_Completo
            FROM Paciente
            ORDER BY Nombre_Completo
        """)

        medicos = consultar_datos("""
            SELECT ID_Medico, Nombre, Apellido
            FROM Medico
            ORDER BY Nombre
        """)

        tipos_examen = consultar_datos("""
            SELECT ID_TipoExamen, Nombre, Area
            FROM Tipo_Examen
            ORDER BY Nombre
        """)

        if not pacientes:
            st.warning("No hay pacientes registrados.")
        elif not tipos_examen:
            st.warning("No hay tipos de examen registrados.")
        else:

            opciones_pacientes = {
                f"{p['Nombre_Completo']} (ID: {p['ID_Paciente']})":
                p["ID_Paciente"]
                for p in pacientes
            }

            paciente_seleccionado = st.selectbox(
                "Seleccionar paciente *",
                list(opciones_pacientes.keys())
            )

            id_paciente = opciones_pacientes[paciente_seleccionado]

            # Buscar citas correspondientes al paciente
            citas = consultar_datos("""
                SELECT ID_Cita, Fecha_Cita, Concepto
                FROM Cita
                WHERE ID_Paciente = %s
                ORDER BY Fecha_Cita DESC
            """, (id_paciente,))

            opciones_medicos = {
                "Sin médico referente": None
            }

            for medico in medicos:
                etiqueta = (
                    f"{medico['Nombre']} {medico['Apellido']} "
                    f"(ID: {medico['ID_Medico']})"
                )
                opciones_medicos[etiqueta] = medico["ID_Medico"]

            opciones_citas = {
                "Sin cita asociada": None
            }

            for cita in citas:
                etiqueta = (
                    f"Cita #{cita['ID_Cita']} - "
                    f"{cita['Fecha_Cita']} - "
                    f"{cita['Concepto'] or 'Sin concepto'}"
                )
                opciones_citas[etiqueta] = cita["ID_Cita"]

            opciones_examenes = {}

            for examen in tipos_examen:
                etiqueta = (
                    f"{examen['Nombre']} - "
                    f"{examen['Area'] or 'Sin área'} "
                    f"(ID: {examen['ID_TipoExamen']})"
                )
                opciones_examenes[etiqueta] = examen["ID_TipoExamen"]

            with st.form("formulario_boleta"):

                st.markdown("### Información de la solicitud")

                medico_seleccionado = st.selectbox(
                    "Médico referente (opcional)",
                    list(opciones_medicos.keys())
                )

                cita_seleccionada = st.selectbox(
                    "Cita asociada (opcional)",
                    list(opciones_citas.keys())
                )

                st.markdown("### Exámenes solicitados")

                examenes_seleccionados = st.multiselect(
                    "Seleccionar uno o varios exámenes *",
                    list(opciones_examenes.keys())
                )

                archivo_boleta = st.text_input(
                    "Archivo de boleta (opcional)",
                    placeholder="Nombre o ruta del archivo"
                )

                guardar = st.form_submit_button(
                    "💾 Registrar boleta",
                    use_container_width=True
                )

            if guardar:

                usuario = st.session_state.get("usuario", {})
                id_user = usuario.get("ID_User")

                if not id_user:
                    st.error(
                        "No se pudo identificar al usuario que registra "
                        "la boleta. Cerrá sesión e ingresá nuevamente."
                    )

                elif not examenes_seleccionados:
                    st.error("Debés seleccionar al menos un examen.")

                else:

                    conexion = None
                    cursor = None

                    try:
                        conexion = obtener_conexion()
                        cursor = conexion.cursor()

                        conexion.start_transaction()

                        # Guardar información general de la boleta
                        consulta_boleta = """
                            INSERT INTO Boleta_Examen
                            (
                                ID_Paciente,
                                ID_Medico,
                                ID_Cita,
                                ID_User,
                                Archivo_Boleta
                            )
                            VALUES (%s, %s, %s, %s, %s)
                        """

                        cursor.execute(
                            consulta_boleta,
                            (
                                id_paciente,
                                opciones_medicos[medico_seleccionado],
                                opciones_citas[cita_seleccionada],
                                id_user,
                                archivo_boleta.strip() or None
                            )
                        )

                        id_boleta = cursor.lastrowid

                        # Guardar los exámenes de la boleta
                        consulta_detalle = """
                            INSERT INTO Detalle_Boleta
                            (ID_Boleta, ID_TipoExamen)
                            VALUES (%s, %s)
                        """

                        detalles = [
                            (
                                id_boleta,
                                opciones_examenes[examen]
                            )
                            for examen in examenes_seleccionados
                        ]

                        cursor.executemany(
                            consulta_detalle,
                            detalles
                        )

                        conexion.commit()

                        st.success(
                            f"¡Boleta #{id_boleta} registrada correctamente!"
                        )

                        st.info(
                            f"Se agregaron {len(detalles)} exámenes "
                            "a la boleta."
                        )

                    except Exception as error:

                        if conexion:
                            conexion.rollback()

                        st.error(
                            f"No se pudo registrar la boleta: {error}"
                        )

                    finally:

                        if cursor:
                            cursor.close()

                        if conexion:
                            conexion.close()

    # ==========================================
    # PESTAÑA 2: CONSULTAR BOLETAS
    # ==========================================

    with pestaña_consulta:

        st.subheader("Boletas registradas")

        try:

            boletas = consultar_datos("""
                SELECT
                    B.ID_Boleta,
                    B.Fecha_Solicitud,
                    P.Nombre_Completo AS Paciente,
                    COALESCE(
                        CONCAT(M.Nombre, ' ', M.Apellido),
                        'Sin médico referente'
                    ) AS Medico,
                    COUNT(D.ID_Detalle) AS Cantidad_Examenes

                FROM Boleta_Examen B

                INNER JOIN Paciente P
                    ON B.ID_Paciente = P.ID_Paciente

                LEFT JOIN Medico M
                    ON B.ID_Medico = M.ID_Medico

                LEFT JOIN Detalle_Boleta D
                    ON B.ID_Boleta = D.ID_Boleta

                GROUP BY
                    B.ID_Boleta,
                    B.Fecha_Solicitud,
                    P.Nombre_Completo,
                    M.Nombre,
                    M.Apellido

                ORDER BY B.ID_Boleta DESC
                LIMIT 100
            """)

            if boletas:

                st.dataframe(
                    boletas,
                    use_container_width=True,
                    hide_index=True
                )

                opciones_boletas = {
                    (
                        f"Boleta #{b['ID_Boleta']} - "
                        f"{b['Paciente']}"
                    ): b["ID_Boleta"]
                    for b in boletas
                }

                seleccion_boleta = st.selectbox(
                    "Seleccionar boleta para ver sus detalles",
                    list(opciones_boletas.keys())
                )

                id_consulta = opciones_boletas[seleccion_boleta]

                detalles = consultar_datos("""
                    SELECT
                        T.Nombre,
                        T.Area

                    FROM Detalle_Boleta D

                    INNER JOIN Tipo_Examen T
                        ON D.ID_TipoExamen = T.ID_TipoExamen

                    WHERE D.ID_Boleta = %s

                    ORDER BY T.Nombre
                """, (id_consulta,))

                st.markdown("### Exámenes incluidos")

                if detalles:

                    st.dataframe(
                        detalles,
                        use_container_width=True,
                        hide_index=True
                    )

                else:
                    st.info("Esta boleta no tiene exámenes asociados.")

            else:

                st.info("Todavía no hay boletas registradas.")

        except Exception as error:

            st.error(
                f"No se pudieron consultar las boletas: {error}"
            )

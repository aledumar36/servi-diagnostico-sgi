import streamlit as st
import os
import uuid

from config.conexion import obtener_conexion


def consultar_datos(consulta, parametros=()):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


def mostrar_boletas():

    st.title("📋 Gestión de boletas de examen")
    st.write(
        "Registro y consulta de boletas de Servi-Diagnóstico."
    )

    pestaña_registro, pestaña_consulta = st.tabs(
        ["📝 Registrar boleta", "🔎 Consultar boletas"]
    )

    # ==========================================
    # REGISTRAR BOLETA
    # ==========================================

    with pestaña_registro:

        st.subheader("Registro de nueva boleta")

        try:
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

        except Exception as error:
            st.error(f"No se pudieron cargar los datos: {error}")
            return

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

            id_paciente = opciones_pacientes[
                paciente_seleccionado
            ]

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
                    f"{medico['Nombre']} "
                    f"{medico['Apellido']} "
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

                st.markdown("### 📎 Archivo de la boleta")

                archivo_boleta = st.file_uploader(
                    "Adjuntar boleta (opcional)",
                    type=["pdf", "jpg", "jpeg", "png"],
                    help="Podés adjuntar un PDF o una fotografía."
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
                        "No se pudo identificar al usuario. "
                        "Cerrá sesión e ingresá nuevamente."
                    )

                elif not examenes_seleccionados:
                    st.error("Debés seleccionar al menos un examen.")

                else:

                    conexion = None
                    cursor = None
                    ruta_archivo = None
                    archivo_guardado = False

                    try:

                        conexion = obtener_conexion()
                        cursor = conexion.cursor()
                        conexion.start_transaction()

                        # Guardar archivo opcional

                        if archivo_boleta is not None:

                            carpeta = "archivos_boletas"
                            os.makedirs(carpeta, exist_ok=True)

                            extension = os.path.splitext(
                                archivo_boleta.name
                            )[1].lower()

                            nombre_archivo = (
                                f"{uuid.uuid4().hex}{extension}"
                            )

                            ruta_archivo = os.path.join(
                                carpeta,
                                nombre_archivo
                            )

                            with open(ruta_archivo, "wb") as archivo:
                                archivo.write(
                                    archivo_boleta.getvalue()
                                )

                            archivo_guardado = True

                        # Registrar boleta

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
                                ruta_archivo
                            )
                        )

                        id_boleta = cursor.lastrowid

                        # Registrar detalles de la boleta

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
                            f"Se agregaron {len(detalles)} exámenes."
                        )

                        if archivo_guardado:
                            st.success(
                                "El archivo se adjuntó correctamente."
                            )
                        else:
                            st.info(
                                "La boleta se registró sin archivo adjunto."
                            )

                    except Exception as error:

                        if conexion:
                            conexion.rollback()

                        if archivo_guardado and ruta_archivo:
                            if os.path.exists(ruta_archivo):
                                os.remove(ruta_archivo)

                        st.error(
                            f"No se pudo registrar la boleta: {error}"
                        )

                    finally:

                        if cursor:
                            cursor.close()

                        if conexion:
                            conexion.close()

    # ==========================================
    # CONSULTAR BOLETAS
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

                id_consulta = opciones_boletas[
                    seleccion_boleta
                ]

                # ==================================
                # MOSTRAR ARCHIVO ADJUNTO
                # ==================================

                st.markdown("### 📎 Archivo adjunto")

                archivo_resultado = consultar_datos("""
                    SELECT Archivo_Boleta
                    FROM Boleta_Examen
                    WHERE ID_Boleta = %s
                """, (id_consulta,))

                if (
                    archivo_resultado
                    and archivo_resultado[0]["Archivo_Boleta"]
                ):

                    ruta = archivo_resultado[0]["Archivo_Boleta"]

                    if os.path.exists(ruta):

                        nombre_archivo = os.path.basename(ruta)

                        with open(ruta, "rb") as archivo:
                            contenido = archivo.read()

                        extension = os.path.splitext(
                            nombre_archivo
                        )[1].lower()

                        if extension == ".pdf":

                            st.download_button(
                                "📄 Descargar boleta PDF",
                                data=contenido,
                                file_name=nombre_archivo,
                                mime="application/pdf"
                            )

                        elif extension in [".jpg", ".jpeg", ".png"]:

                            st.image(
                                contenido,
                                caption="Imagen de la boleta",
                                use_container_width=True
                            )

                            mime = (
                                "image/png"
                                if extension == ".png"
                                else "image/jpeg"
                            )

                            st.download_button(
                                "📥 Descargar imagen",
                                data=contenido,
                                file_name=nombre_archivo,
                                mime=mime
                            )

                    else:

                        st.warning(
                            "El archivo figura en la base de datos, "
                            "pero no se encuentra en el almacenamiento."
                        )

                else:

                    st.info(
                        "Esta boleta no tiene ningún archivo adjunto."
                    )

                # ==================================
                # MOSTRAR EXÁMENES DE LA BOLETA
                # ==================================

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

                    st.info(
                        "Esta boleta no tiene exámenes asociados."
                    )

            else:

                st.info("Todavía no hay boletas registradas.")

        except Exception as error:

            st.error(
                f"No se pudieron consultar las boletas: {error}"
            )

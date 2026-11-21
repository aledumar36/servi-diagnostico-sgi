import streamlit as st
from config.conexion import obtener_conexion


def mostrar_expedientes():
    """Atenciones médicas y solicitudes de exámenes vinculadas a citas."""
    usuario = st.session_state.get("usuario", {})
    if not st.session_state.get("autenticado") or not isinstance(usuario, dict):
        st.error("Debes iniciar sesión.")
        return
    if str(usuario.get("Rol", "")).strip().lower() not in ("medico", "médico"):
        st.error("Este módulo es exclusivo del médico.")
        return

    st.title("🩺 Expedientes médicos")
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT U.ID_Medico, M.Nombre, M.Apellido
            FROM Usuario_Sistema U
            INNER JOIN Medico M ON M.ID_Medico = U.ID_Medico
            WHERE U.ID_User = %s AND U.ID_Rol = 3 AND U.Estado = 'Activo'
        """, (usuario["ID_User"],))
        medico = cursor.fetchone()
        if not medico:
            st.error("La cuenta no está vinculada a un médico activo.")
            return
        id_medico = medico["ID_Medico"]
        st.caption(f"Médico responsable: {medico['Nombre']} {medico['Apellido']}")

        tab_registro, tab_historial = st.tabs(["Registrar consulta", "Historial clínico"])
        with tab_registro:
            cursor.execute("""
                SELECT C.ID_Cita, C.ID_Paciente, C.Fecha_Cita, C.Concepto,
                       P.Nombre_Completo
                FROM Cita C
                INNER JOIN Paciente P ON P.ID_Paciente = C.ID_Paciente
                LEFT JOIN Expediente_Medico E ON E.ID_Cita = C.ID_Cita
                WHERE C.ID_Medico = %s AND E.ID_Expediente IS NULL
                ORDER BY C.Fecha_Cita DESC
            """, (id_medico,))
            citas = cursor.fetchall()
            if not citas:
                st.info("No hay citas asignadas pendientes de registrar.")
            else:
                citas_por_id = {c["ID_Cita"]: c for c in citas}
                id_cita = st.selectbox(
                    "Cita asignada *",
                    options=list(citas_por_id),
                    format_func=lambda k: (
                        f"#{k} · {citas_por_id[k]['Nombre_Completo']} · "
                        f"{citas_por_id[k]['Fecha_Cita']}"
                    ),
                )
                cita = citas_por_id[id_cita]
                st.write(f"**Paciente:** {cita['Nombre_Completo']}")
                st.write(f"**Concepto de cita:** {cita['Concepto'] or 'No especificado'}")

                cursor.execute("""
                    SELECT ID_TipoExamen, Nombre, Area
                    FROM Tipo_Examen ORDER BY Area, Nombre, ID_TipoExamen
                """)
                catalogo = cursor.fetchall()
                examenes_por_id = {e["ID_TipoExamen"]: e for e in catalogo}

                with st.form("form_expediente_medico"):
                    motivo = st.text_area("Motivo de consulta *")
                    observaciones = st.text_area("Observaciones clínicas")
                    diagnostico = st.text_area("Diagnóstico o impresión clínica")
                    tratamiento = st.text_area("Tratamiento e indicaciones")
                    st.markdown("#### Solicitud de exámenes (opcional)")
                    seleccionados = st.multiselect(
                        "Exámenes solicitados",
                        options=list(examenes_por_id),
                        format_func=lambda k: (
                            f"{examenes_por_id[k]['Nombre']} "
                            f"({examenes_por_id[k]['Area']}) · ID {k}"
                        ),
                    )
                    guardar = st.form_submit_button("Guardar consulta", type="primary")

                if guardar:
                    if not motivo.strip():
                        st.warning("Ingresá el motivo de consulta.")
                    else:
                        try:
                            # Cerrar la transacción implícita iniciada por las consultas SELECT.
                            conexion.commit()
                            conexion.start_transaction()
                            # Verificar autorización nuevamente al momento de guardar.
                            cursor.execute("""
                                SELECT C.ID_Paciente
                                FROM Cita C
                                LEFT JOIN Expediente_Medico E ON E.ID_Cita = C.ID_Cita
                                WHERE C.ID_Cita = %s AND C.ID_Medico = %s
                                  AND E.ID_Expediente IS NULL
                                FOR UPDATE
                            """, (id_cita, id_medico))
                            autorizada = cursor.fetchone()
                            if not autorizada:
                                raise ValueError("La cita ya fue atendida o no está asignada a este médico.")
                            id_paciente = autorizada["ID_Paciente"]
                            cursor.execute("""
                                INSERT INTO Expediente_Medico
                                    (ID_Paciente, ID_Medico, ID_Cita,
                                     Motivo_Consulta, Observaciones, Diagnostico, Tratamiento)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                id_paciente, id_medico, id_cita,
                                motivo.strip(), observaciones.strip(),
                                diagnostico.strip(), tratamiento.strip(),
                            ))
                            id_expediente = cursor.lastrowid
                            id_boleta = None
                            if seleccionados:
                                cursor.execute("""
                                    INSERT INTO Boleta_Examen
                                        (ID_Paciente, ID_Medico, ID_Cita, ID_User)
                                    VALUES (%s, %s, %s, %s)
                                """, (id_paciente, id_medico, id_cita, usuario["ID_User"]))
                                id_boleta = cursor.lastrowid
                                cursor.executemany("""
                                    INSERT INTO Detalle_Boleta (ID_Boleta, ID_TipoExamen)
                                    VALUES (%s, %s)
                                """, [(id_boleta, tipo) for tipo in seleccionados])
                                cursor.executemany("""
                                    INSERT INTO Examen
                                        (ID_Boleta, ID_Paciente, ID_TipoExamen,
                                         ID_User_Registra, Fecha_Realizacion, Estado)
                                    VALUES (%s, %s, %s, %s, NULL, 'Pendiente')
                                """, [
                                    (id_boleta, id_paciente, tipo, usuario["ID_User"])
                                    for tipo in seleccionados
                                ])
                            conexion.commit()
                            st.success(f"Consulta #{id_expediente} registrada correctamente.")
                            if id_boleta:
                                st.success(f"Boleta #{id_boleta} generada con {len(seleccionados)} examen(es) pendiente(s).")
                            st.info("Para registrar otra consulta, actualizá esta página.")
                        except Exception as error:
                            conexion.rollback()
                            st.error("No fue posible guardar la consulta y la boleta. No se registraron cambios parciales.")
                            st.write("Tipo de error:", type(error).__name__)
                            if hasattr(error, "errno") and error.errno is not None:
                                st.write("Código MySQL:", error.errno)
                            if isinstance(error, ValueError):
                                st.warning(str(error))
                            elif getattr(error, "errno", None) == 1062:
                                st.warning("Hay un registro duplicado. Verificá si esta cita ya tiene expediente o boleta.")
                            elif getattr(error, "errno", None) == 1452:
                                st.warning("Falta una referencia válida en la base de datos (llave foránea).")

        with tab_historial:
            # Solo se muestran pacientes con cita vinculada a este médico.
            cursor.execute("""
                SELECT DISTINCT P.ID_Paciente, P.Nombre_Completo
                FROM Paciente P
                INNER JOIN Cita C ON C.ID_Paciente = P.ID_Paciente
                WHERE C.ID_Medico = %s
                ORDER BY P.Nombre_Completo
            """, (id_medico,))
            pacientes = cursor.fetchall()
            if not pacientes:
                st.info("No tenés pacientes vinculados por citas.")
            else:
                pacientes_por_id = {p["ID_Paciente"]: p for p in pacientes}
                id_paciente = st.selectbox(
                    "Paciente",
                    list(pacientes_por_id),
                    format_func=lambda k: pacientes_por_id[k]["Nombre_Completo"],
                    key="paciente_historial_medico",
                )
                # Para la primera versión, solo las notas creadas por este médico.
                cursor.execute("""
                    SELECT E.ID_Expediente, E.Fecha, E.ID_Cita,
                           E.Motivo_Consulta, E.Observaciones,
                           E.Diagnostico, E.Tratamiento
                    FROM Expediente_Medico E
                    WHERE E.ID_Paciente = %s AND E.ID_Medico = %s
                      AND EXISTS (
                          SELECT 1 FROM Cita C
                          WHERE C.ID_Paciente = E.ID_Paciente
                            AND C.ID_Medico = %s
                      )
                    ORDER BY E.Fecha DESC, E.ID_Expediente DESC
                """, (id_paciente, id_medico, id_medico))
                registros = cursor.fetchall()
                if not registros:
                    st.info("Aún no hay atenciones registradas por este médico.")
                for registro in registros:
                    with st.expander(
                        f"Atención #{registro['ID_Expediente']} · {registro['Fecha']}"
                    ):
                        st.write(f"**Cita:** {registro['ID_Cita'] or 'Sin cita'}")
                        st.write(f"**Motivo:** {registro['Motivo_Consulta'] or '—'}")
                        st.write(f"**Observaciones:** {registro['Observaciones'] or '—'}")
                        st.write(f"**Diagnóstico:** {registro['Diagnostico'] or '—'}")
                        st.write(f"**Tratamiento:** {registro['Tratamiento'] or '—'}")

                        # Mostrar exámenes solicitados desde esta cita.
                        if registro["ID_Cita"] is not None:
                            cursor.execute("""
                                SELECT B.ID_Boleta, T.Nombre, T.Area,
                                       X.Estado AS Estado_Examen
                                FROM Boleta_Examen B
                                INNER JOIN Detalle_Boleta D
                                    ON D.ID_Boleta = B.ID_Boleta
                                INNER JOIN Tipo_Examen T
                                    ON T.ID_TipoExamen = D.ID_TipoExamen
                                LEFT JOIN Examen X
                                    ON X.ID_Boleta = B.ID_Boleta
                                   AND X.ID_TipoExamen = D.ID_TipoExamen
                                WHERE B.ID_Cita = %s
                                  AND B.ID_Paciente = %s
                                  AND B.ID_Medico = %s
                                ORDER BY B.ID_Boleta, T.Area, T.Nombre
                            """, (registro["ID_Cita"], id_paciente, id_medico))
                            examenes_solicitados = cursor.fetchall()
                            st.markdown("**🧪 Exámenes solicitados**")
                            if examenes_solicitados:
                                for examen in examenes_solicitados:
                                    estado = examen["Estado_Examen"] or "Sin estado registrado"
                                    st.write(
                                        f"• {examen['Nombre']} ({examen['Area']}) "
                                        f"— {estado} · Boleta #{examen['ID_Boleta']}"
                                    )
                            else:
                                st.caption("No hay exámenes solicitados vinculados a esta cita.")
                        else:
                            st.caption("Este expediente no está vinculado a una cita.")
    except Exception:
        st.error("No se pudo cargar el módulo de expedientes. Revisá la conexión y el esquema de MySQL.")
    finally:
        if cursor is not None:
            cursor.close()
        if conexion is not None:
            conexion.close()

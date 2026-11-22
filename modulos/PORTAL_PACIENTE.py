from pathlib import Path
import streamlit as st
from config.conexion import obtener_conexion


def _consultar(sql, parametros=()):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(sql, parametros)
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


def mostrar_portal_paciente():
    usuario = st.session_state.get('usuario')
    if (not st.session_state.get('autenticado') or not isinstance(usuario, dict)
            or str(usuario.get('Rol', '')).strip().lower() != 'paciente'):
        st.error('Acceso exclusivo para pacientes.')
        return
    id_paciente = usuario.get('ID_Paciente')
    if not id_paciente:
        st.error('Tu cuenta no está vinculada a un paciente. Solicitá ayuda al administrador.')
        return

    st.title('👤 Mi portal de paciente')
    try:
        pacientes = _consultar('''SELECT ID_Paciente, Nombre_Completo, Fecha_Nacimiento,
                                Telefono, Correo FROM Paciente WHERE ID_Paciente=%s''', (id_paciente,))
        if not pacientes:
            st.error('No se encontró el registro del paciente vinculado a tu cuenta.')
            return
        paciente = pacientes[0]
        pestaña_datos, pestaña_citas, pestaña_resultados = st.tabs(
            ['Mis datos', 'Mis citas', 'Mis exámenes y resultados'])

        with pestaña_datos:
            st.write(f"**Nombre:** {paciente['Nombre_Completo']}")
            st.write(f"**Fecha de nacimiento:** {paciente['Fecha_Nacimiento'] or 'No registrada'}")
            st.write(f"**Teléfono:** {paciente['Telefono'] or 'No registrado'}")
            st.write(f"**Correo:** {paciente['Correo'] or 'No registrado'}")

        with pestaña_citas:
            citas = _consultar('''SELECT C.ID_Cita, C.Fecha_Cita, C.Concepto,
                                  M.Nombre AS Nombre_Medico, M.Apellido AS Apellido_Medico
                                  FROM Cita C LEFT JOIN Medico M ON M.ID_Medico=C.ID_Medico
                                  WHERE C.ID_Paciente=%s ORDER BY C.Fecha_Cita DESC''', (id_paciente,))
            if not citas:
                st.info('No tenés citas registradas.')
            else:
                st.dataframe([{'Cita': c['ID_Cita'], 'Fecha': c['Fecha_Cita'],
                               'Concepto': c['Concepto'] or '',
                               'Médico': f"{c['Nombre_Medico'] or ''} {c['Apellido_Medico'] or ''}".strip()}
                              for c in citas], use_container_width=True, hide_index=True)

        with pestaña_resultados:
            examenes = _consultar('''SELECT E.ID_Examen, E.ID_Boleta, E.Estado,
                                   E.Fecha_Realizacion, T.Nombre AS Nombre_Examen
                                   FROM Examen E JOIN Tipo_Examen T
                                   ON T.ID_TipoExamen=E.ID_TipoExamen
                                   WHERE E.ID_Paciente=%s
                                   ORDER BY E.ID_Examen DESC''', (id_paciente,))
            if not examenes:
                st.info('No tenés exámenes registrados.')
                return
            st.dataframe([{'Examen': e['Nombre_Examen'], 'Boleta': e['ID_Boleta'],
                           'Fecha': e['Fecha_Realizacion'], 'Estado': e['Estado']}
                          for e in examenes], use_container_width=True, hide_index=True)
            st.caption('Los archivos se muestran cuando el laboratorio ha cargado el resultado previamente firmado y sellado.')

            # Nunca confiar en un ID de paciente ingresado desde la interfaz.
            # Además, excluir archivos compartidos con exámenes de otros pacientes
            # o con exámenes todavía no validados.
            archivos = _consultar('''
                SELECT DISTINCT E.ID_Examen, T.Nombre AS Nombre_Examen,
                       A.ID_Archivo, A.Nombre_Archivo, A.Ruta_Archivo, A.Tipo_Archivo
                FROM Examen E
                JOIN Tipo_Examen T ON T.ID_TipoExamen=E.ID_TipoExamen
                JOIN Examen_Archivo EA ON EA.ID_Examen=E.ID_Examen
                JOIN Archivo_Resultado A ON A.ID_Archivo=EA.ID_Archivo
                WHERE E.ID_Paciente=%s AND E.Estado='Resultado cargado'
                  AND NOT EXISTS (
                      SELECT 1 FROM Examen_Archivo EA2
                      JOIN Examen E2 ON E2.ID_Examen=EA2.ID_Examen
                      WHERE EA2.ID_Archivo=A.ID_Archivo
                        AND (E2.ID_Paciente<>%s OR E2.Estado<>'Resultado cargado')
                  )
                ORDER BY E.ID_Examen DESC, A.ID_Archivo DESC
            ''', (id_paciente, id_paciente))
            if not archivos:
                st.info('Aún no hay archivos de resultados disponibles para descargar.')
                return
            for archivo in archivos:
                with st.expander(f"{archivo['Nombre_Examen']} — {archivo['Nombre_Archivo']}"):
                    ruta = Path(archivo['Ruta_Archivo'])
                    # Solo aceptar archivos guardados en la carpeta controlada por el módulo.
                    carpeta = Path('archivos_resultados').resolve()
                    if not ruta.resolve().is_relative_to(carpeta) or not ruta.is_file():
                        st.warning('El archivo no está disponible. Contactá al laboratorio.')
                        continue
                    contenido = ruta.read_bytes()
                    st.download_button('📥 Descargar resultado', data=contenido,
                                       file_name=Path(archivo['Nombre_Archivo']).name,
                                       mime=archivo['Tipo_Archivo'],
                                       key=f"paciente_archivo_{archivo['ID_Examen']}_{archivo['ID_Archivo']}")
    except Exception:
        st.error('No fue posible cargar tu información. Intentá nuevamente o contactá al laboratorio.')

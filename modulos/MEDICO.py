import streamlit as st
from datetime import date, datetime
from pathlib import Path
from config.conexion import obtener_conexion


def fecha_legible(valor):
    if valor is None:
        return 'No registrada'
    if isinstance(valor, (date, datetime)):
        return valor.strftime('%d/%m/%Y')
    try:
        return datetime.fromisoformat(str(valor)).strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(valor)


def codigo_paciente(id_paciente):
    return f"P-{int(id_paciente):06d}"


def mostrar_medico():
    st.title('🩺 Portal del médico')
    usuario = st.session_state.get('usuario', {})
    if not isinstance(usuario, dict) or str(usuario.get('Rol', '')).strip().lower() not in ('medico', 'médico'):
        st.error('No tenés permiso para acceder a este módulo.')
        return

    id_user = usuario.get('ID_User')
    if not id_user:
        st.error('No se pudo identificar al usuario autenticado.')
        return

    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute('''
            SELECT U.ID_Medico, M.Nombre, M.Apellido
            FROM Usuario_Sistema U
            INNER JOIN Medico M ON U.ID_Medico = M.ID_Medico
            WHERE U.ID_User = %s AND U.ID_Rol = 3 AND U.Estado = 'Activo'
        ''', (id_user,))
        medico = cursor.fetchone()
        if not medico:
            st.warning('Tu cuenta todavía no está vinculada con un médico registrado.')
            return

        id_medico = medico['ID_Medico']
        st.success(f"Bienvenido, Dr./Dra. {medico['Nombre']} {medico['Apellido']}")
        pestaña_citas, pestaña_pacientes, pestaña_resultados = st.tabs([
            '📅 Mis citas', '👥 Mis pacientes', '🧪 Resultados de laboratorio'
        ])

        with pestaña_citas:
            st.subheader('Citas asignadas')
            cursor.execute('''
                SELECT C.ID_Cita, P.ID_Paciente, P.Nombre_Completo,
                       P.Fecha_Nacimiento, C.Fecha_Cita, C.Concepto
                FROM Cita C
                INNER JOIN Paciente P ON C.ID_Paciente = P.ID_Paciente
                WHERE C.ID_Medico = %s
                ORDER BY C.Fecha_Cita DESC
            ''', (id_medico,))
            citas = cursor.fetchall()
            if citas:
                st.dataframe([{
                    'Cita': c['ID_Cita'],
                    'Código paciente': codigo_paciente(c['ID_Paciente']),
                    'Paciente': c['Nombre_Completo'],
                    'Nacimiento': fecha_legible(c['Fecha_Nacimiento']),
                    'Fecha de cita': c['Fecha_Cita'],
                    'Concepto': c['Concepto']
                } for c in citas], use_container_width=True, hide_index=True)
            else:
                st.info('Todavía no tenés citas asignadas.')

        # Solo pacientes con cita O boleta explícitamente asociada a este médico.
        cursor.execute('''
            SELECT P.ID_Paciente, P.Nombre_Completo, P.Fecha_Nacimiento, P.DUI
            FROM Paciente P
            WHERE EXISTS (
                SELECT 1 FROM Cita C
                WHERE C.ID_Paciente = P.ID_Paciente AND C.ID_Medico = %s
            ) OR EXISTS (
                SELECT 1 FROM Boleta_Examen B
                WHERE B.ID_Paciente = P.ID_Paciente AND B.ID_Medico = %s
            )
            ORDER BY P.Nombre_Completo, P.ID_Paciente
        ''', (id_medico, id_medico))
        pacientes = cursor.fetchall()

        with pestaña_pacientes:
            st.subheader('Mis pacientes vinculados')
            st.caption('Pacientes con citas o boletas asociadas a tu cuenta médica.')
            if pacientes:
                busqueda_pacientes = st.text_input(
                    'Buscar por código, nombre o DUI', key='medico_busqueda_pacientes'
                ).strip().casefold()
                filtrados = [p for p in pacientes if busqueda_pacientes in (
                    codigo_paciente(p['ID_Paciente']) + ' ' +
                    str(p['ID_Paciente']) + ' ' +
                    p['Nombre_Completo'] + ' ' + (p['DUI'] or '')
                ).casefold()]
                st.caption(f'{len(filtrados)} paciente(s) encontrado(s)')
                if filtrados:
                    st.dataframe([{
                        'Código': codigo_paciente(p['ID_Paciente']),
                        'Nombre completo': p['Nombre_Completo'],
                        'Nacimiento': fecha_legible(p['Fecha_Nacimiento'])
                    } for p in filtrados], use_container_width=True, hide_index=True)
                else:
                    st.info('No se encontraron pacientes con esa búsqueda.')
            else:
                st.info('Todavía no tenés pacientes vinculados.')

        with pestaña_resultados:
            st.subheader('Consultar resultados de laboratorio')
            st.caption('Solo se muestran resultados de boletas asociadas a este médico.')
            if not pacientes:
                st.info('No hay pacientes vinculados para consultar.')
            else:
                busqueda = st.text_input(
                    'Buscar paciente por código, nombre o DUI',
                    key='medico_busqueda_resultados'
                ).strip().casefold()
                coincidentes = [p for p in pacientes if busqueda in (
                    codigo_paciente(p['ID_Paciente']) + ' ' +
                    str(p['ID_Paciente']) + ' ' +
                    p['Nombre_Completo'] + ' ' + (p['DUI'] or '')
                ).casefold()]
                if not coincidentes:
                    st.info('No se encontraron pacientes con esa búsqueda.')
                else:
                    paciente = st.selectbox(
                        'Seleccionar paciente', coincidentes,
                        format_func=lambda p: (
                            f"{codigo_paciente(p['ID_Paciente'])} | "
                            f"{p['Nombre_Completo']} | Nac.: {fecha_legible(p['Fecha_Nacimiento'])}"
                        ), key='medico_paciente_resultados'
                    )
                    # Filtrado por médico EN LA CONSULTA SQL, no solo en la interfaz.
                    cursor.execute('''
                        SELECT B.ID_Boleta, B.Fecha_Solicitud,
                               E.ID_Examen, T.Nombre AS Examen, T.Area,
                               E.Estado, E.Fecha_Realizacion
                        FROM Boleta_Examen B
                        INNER JOIN Examen E ON E.ID_Boleta = B.ID_Boleta
                        INNER JOIN Tipo_Examen T ON T.ID_TipoExamen = E.ID_TipoExamen
                        WHERE B.ID_Medico = %s AND B.ID_Paciente = %s
                          AND E.ID_Paciente = B.ID_Paciente
                        ORDER BY B.Fecha_Solicitud DESC, E.ID_Examen DESC
                    ''', (id_medico, paciente['ID_Paciente']))
                    examenes = cursor.fetchall()
                    if not examenes:
                        st.info('Este paciente no tiene exámenes asociados a tus boletas.')
                    else:
                        st.dataframe([{
                            'Boleta': f"#{e['ID_Boleta']}",
                            'Fecha solicitud': fecha_legible(e['Fecha_Solicitud']),
                            'Examen': e['Examen'], 'Área': e['Area'],
                            'Estado': e['Estado'],
                            'Fecha realización': fecha_legible(e['Fecha_Realizacion'])
                        } for e in examenes], use_container_width=True, hide_index=True)
                        # Solo documentos de los exámenes autorizados para este médico.
                        cursor.execute('''
                            SELECT E.ID_Examen, T.Nombre AS Examen,
                                   A.ID_Archivo, A.Nombre_Archivo,
                                   A.Ruta_Archivo, A.Tipo_Archivo
                            FROM Boleta_Examen B
                            INNER JOIN Examen E ON E.ID_Boleta = B.ID_Boleta
                            INNER JOIN Tipo_Examen T ON T.ID_TipoExamen = E.ID_TipoExamen
                            INNER JOIN Examen_Archivo EA ON EA.ID_Examen = E.ID_Examen
                            INNER JOIN Archivo_Resultado A ON A.ID_Archivo = EA.ID_Archivo
                            WHERE B.ID_Medico = %s AND B.ID_Paciente = %s
                              AND E.ID_Paciente = B.ID_Paciente
                            ORDER BY E.ID_Examen DESC, A.ID_Archivo DESC
                        ''', (id_medico, paciente['ID_Paciente']))
                        archivos = cursor.fetchall()
                        st.markdown('#### Archivos de resultados')
                        if not archivos:
                            st.info('Todavía no hay documentos de resultados cargados.')
                        for a in archivos:
                            with st.expander(
                                f"{a['Examen']} · {a['Nombre_Archivo']} (#{a['ID_Archivo']})"
                            ):
                                ruta = Path(a['Ruta_Archivo'])
                                if not ruta.is_file():
                                    st.warning('Este archivo no está disponible en el almacenamiento.')
                                    continue
                                contenido = ruta.read_bytes()
                                st.download_button(
                                    '📥 Descargar resultado', data=contenido,
                                    file_name=Path(a['Nombre_Archivo']).name,
                                    mime=a['Tipo_Archivo'] or 'application/octet-stream',
                                    key=f"medico_descarga_{a['ID_Examen']}_{a['ID_Archivo']}"
                                )
                                if str(a['Tipo_Archivo'] or '').startswith('image/'):
                                    st.image(contenido, use_container_width=True)
    except Exception as error:
        st.error('No fue posible cargar la información del médico.')
        st.error(str(error))
    finally:
        if cursor is not None:
            cursor.close()
        if conexion is not None:
            conexion.close()

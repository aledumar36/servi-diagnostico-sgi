import os
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
from config.conexion import obtener_conexion

CARPETA = Path('archivos_resultados')
EXTENSIONES = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}


def consultar(sql, parametros=()):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(sql, parametros)
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


def obtener_usuario():
    usuario = st.session_state.get('usuario', {})
    if not isinstance(usuario, dict):
        return None
    return usuario.get('ID_User')


def obtener_examenes(id_boleta):
    return consultar('''
        SELECT E.ID_Examen, E.ID_TipoExamen, T.Nombre, T.Area,
               E.Estado, E.Fecha_Realizacion,
               COUNT(EA.ID_ExamenArchivo) AS Cantidad_Archivos
        FROM Examen E
        JOIN Tipo_Examen T ON T.ID_TipoExamen = E.ID_TipoExamen
        LEFT JOIN Examen_Archivo EA ON EA.ID_Examen = E.ID_Examen
        WHERE E.ID_Boleta = %s
        GROUP BY E.ID_Examen, E.ID_TipoExamen, T.Nombre, T.Area,
                 E.Estado, E.Fecha_Realizacion
        ORDER BY T.Nombre, E.ID_Examen
    ''', (id_boleta,))


def etiqueta_examen(examen):
    return f"#{examen['ID_Examen']} - {examen['Nombre']} ({examen['Estado']})"


def actualizar_estados(cursor, ids_examen):
    for id_examen in ids_examen:
        cursor.execute('''
            SELECT COUNT(*) FROM Examen_Archivo WHERE ID_Examen = %s
        ''', (id_examen,))
        cantidad = cursor.fetchone()[0]
        if cantidad:
            cursor.execute('''
                UPDATE Examen SET Estado = 'Resultado cargado',
                    Fecha_Realizacion = COALESCE(Fecha_Realizacion, CURDATE())
                WHERE ID_Examen = %s
            ''', (id_examen,))
        else:
            cursor.execute('''
                UPDATE Examen SET Estado = 'Pendiente', Fecha_Realizacion = NULL
                WHERE ID_Examen = %s
            ''', (id_examen,))


def guardar_resultados(id_boleta, ids_examen, archivos, id_usuario, fecha_realizacion):
    conexion = None
    cursor = None
    rutas_creadas = []
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        conexion.start_transaction()

        # Verificar que todos los exámenes pertenecen a la boleta elegida.
        marcadores = ','.join(['%s'] * len(ids_examen))
        cursor.execute(
            f'SELECT ID_Examen FROM Examen WHERE ID_Boleta = %s AND ID_Examen IN ({marcadores}) FOR UPDATE',
            (id_boleta, *ids_examen)
        )
        encontrados = {fila[0] for fila in cursor.fetchall()}
        if encontrados != set(ids_examen):
            raise ValueError('Uno o más exámenes no pertenecen a esta boleta.')

        CARPETA.mkdir(parents=True, exist_ok=True)
        for archivo in archivos:
            extension = Path(archivo.name).suffix.lower()
            if extension not in EXTENSIONES:
                raise ValueError('Formato no permitido. Solo PDF, JPG, JPEG o PNG.')
            contenido = archivo.getvalue()
            if not contenido:
                raise ValueError('Uno de los archivos está vacío.')
            if len(contenido) > 10 * 1024 * 1024:
                raise ValueError('Cada archivo debe tener un máximo de 10 MB.')

            nombre_interno = f'{uuid.uuid4().hex}{extension}'
            ruta = CARPETA / nombre_interno
            with open(ruta, 'wb') as destino:
                destino.write(contenido)
            rutas_creadas.append(ruta)

            cursor.execute('''
                INSERT INTO Archivo_Resultado
                    (ID_User, Nombre_Archivo, Ruta_Archivo, Tipo_Archivo)
                VALUES (%s, %s, %s, %s)
            ''', (id_usuario, os.path.basename(archivo.name), str(ruta), EXTENSIONES[extension]))
            id_archivo = cursor.lastrowid

            cursor.executemany('''
                INSERT INTO Examen_Archivo (ID_Examen, ID_Archivo)
                VALUES (%s, %s)
            ''', [(id_examen, id_archivo) for id_examen in ids_examen])

        cursor.executemany('''
            UPDATE Examen SET Fecha_Realizacion = %s
            WHERE ID_Examen = %s
        ''', [(fecha_realizacion, id_examen) for id_examen in ids_examen])
        actualizar_estados(cursor, ids_examen)
        conexion.commit()
        return True, f'Se guardaron {len(archivos)} archivo(s) para {len(ids_examen)} examen(es).'
    except Exception as error:
        if conexion:
            conexion.rollback()
        for ruta in rutas_creadas:
            try:
                ruta.unlink(missing_ok=True)
            except OSError:
                pass
        return False, str(error)
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


def quitar_asociacion(id_examen, id_archivo):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        conexion.start_transaction()
        cursor.execute('''
            DELETE FROM Examen_Archivo
            WHERE ID_Examen = %s AND ID_Archivo = %s
        ''', (id_examen, id_archivo))
        if cursor.rowcount != 1:
            raise ValueError('La asociación ya no existe.')
        actualizar_estados(cursor, [id_examen])
        # Conservar el registro de Archivo_Resultado para trazabilidad.
        conexion.commit()
        return True, 'Se retiró la asociación. El archivo permanece en Archivo_Resultado, pero esta versión no conserva el historial de asociaciones retiradas.'
    except Exception as error:
        if conexion:
            conexion.rollback()
        return False, str(error)
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


def mostrar_resultados():
    st.title('🧪 Resultados de exámenes')
    st.caption('Control de pendientes, carga y consulta de resultados por origen de la solicitud.')

    usuario = st.session_state.get('usuario', {})
    rol = str(usuario.get('Rol', '')).strip().lower() if isinstance(usuario, dict) else ''
    if not st.session_state.get('autenticado') or rol not in ('regente-administrador', 'secretario'):
        st.error('No tenés permiso para acceder a este módulo.')
        return

    id_usuario = obtener_usuario()
    if not id_usuario:
        st.error('No se pudo identificar al usuario. Cerrá sesión e ingresá nuevamente.')
        return

    # Contamos exámenes, no boletas: una boleta puede incluir varias pruebas.
    try:
        resumen = consultar("""
            SELECT
                CASE WHEN B.ID_Medico IS NULL THEN 'Sin médico' ELSE 'Con médico' END AS Grupo,
                COUNT(E.ID_Examen) AS Total,
                SUM(CASE WHEN E.Estado = 'Pendiente' THEN 1 ELSE 0 END) AS Pendientes,
                SUM(CASE WHEN E.Estado = 'Resultado cargado' THEN 1 ELSE 0 END) AS Cargados
            FROM Boleta_Examen B
            INNER JOIN Examen E ON E.ID_Boleta = B.ID_Boleta
            GROUP BY CASE WHEN B.ID_Medico IS NULL THEN 'Sin médico' ELSE 'Con médico' END
        """)
    except Exception as error:
        st.error(f'No se pudo consultar el resumen de exámenes: {error}')
        return

    totales = {r['Grupo']: r for r in resumen}
    col_medico, col_directo = st.columns(2)
    for columna, grupo, titulo in (
        (col_medico, 'Con médico', '🩺 Con médico asociado'),
        (col_directo, 'Sin médico', '🧪 Servi-Diagnóstico'),
    ):
        datos = totales.get(grupo, {})
        with columna:
            st.markdown(f'**{titulo}**')
            st.metric('Exámenes pendientes', int(datos.get('Pendientes') or 0))
            st.caption(
                f"Resultados cargados: {int(datos.get('Cargados') or 0)} · "
                f"Total de exámenes: {int(datos.get('Total') or 0)}"
            )

    st.divider()
    grupo_seleccionado = st.radio(
        'Origen de la solicitud',
        ['Con médico asociado', 'Servi-Diagnóstico'],
        horizontal=True,
        key='resultados_origen',
    )
    con_medico = grupo_seleccionado == 'Con médico asociado'
    filtro_medico = 'B.ID_Medico IS NOT NULL' if con_medico else 'B.ID_Medico IS NULL'

    try:
        boletas = consultar(f"""
            SELECT B.ID_Boleta, B.Fecha_Solicitud, B.ID_Paciente,
                   P.Nombre_Completo, P.Fecha_Nacimiento,
                   M.Nombre AS Nombre_Medico, M.Apellido AS Apellido_Medico,
                   COUNT(E.ID_Examen) AS Total_Examenes,
                   SUM(CASE WHEN E.Estado = 'Pendiente' THEN 1 ELSE 0 END) AS Pendientes
            FROM Boleta_Examen B
            INNER JOIN Paciente P ON P.ID_Paciente = B.ID_Paciente
            LEFT JOIN Medico M ON M.ID_Medico = B.ID_Medico
            LEFT JOIN Examen E ON E.ID_Boleta = B.ID_Boleta
            WHERE {filtro_medico}
            GROUP BY B.ID_Boleta, B.Fecha_Solicitud, B.ID_Paciente,
                     P.Nombre_Completo, P.Fecha_Nacimiento, M.Nombre, M.Apellido
            ORDER BY B.ID_Boleta DESC
            LIMIT 200
        """)
    except Exception as error:
        st.error(f'No se pudieron cargar las boletas: {error}')
        return

    if not boletas:
        st.info('No hay boletas registradas en esta categoría.')
        return

    solo_pendientes = st.checkbox('Mostrar solo boletas con exámenes pendientes', key='resultados_solo_pendientes')
    if solo_pendientes:
        boletas = [b for b in boletas if int(b['Pendientes'] or 0) > 0]
    if not boletas:
        st.info('No hay boletas pendientes en las últimas 200 boletas de esta categoría.')
        return

    opciones_boletas = {}
    for b in boletas:
        nacimiento = b['Fecha_Nacimiento']
        nacimiento_texto = nacimiento.strftime('%d/%m/%Y') if hasattr(nacimiento, 'strftime') else str(nacimiento or 'No registrada')
        medico_texto = ''
        if con_medico:
            medico_texto = f" · Médico: {b['Nombre_Medico'] or ''} {b['Apellido_Medico'] or ''}"
        etiqueta = (
            f"Boleta #{b['ID_Boleta']} · P-{b['ID_Paciente']:06d} · "
            f"{b['Nombre_Completo']} · Nac.: {nacimiento_texto} · "
            f"Pendientes: {int(b['Pendientes'] or 0)}{medico_texto}"
        )
        opciones_boletas[etiqueta] = b['ID_Boleta']

    seleccion = st.selectbox('Seleccionar boleta', list(opciones_boletas), key='resultados_boleta')
    id_boleta = opciones_boletas[seleccion]
    st.caption('El estado se obtiene de la tabla Examen. Las boletas sin exámenes registrados no se contabilizan como pendientes.')

    try:
        examenes = obtener_examenes(id_boleta)
    except Exception as error:
        st.error(f'No se pudieron cargar los exámenes: {error}')
        return

    if not examenes:
        st.warning('Esta boleta no tiene registros en Examen. Las boletas anteriores a la actualización pueden requerir sincronización.')
        return

    st.dataframe([
        {'ID': e['ID_Examen'], 'Examen': e['Nombre'], 'Área': e['Area'],
         'Estado': e['Estado'], 'Archivos': e['Cantidad_Archivos']}
        for e in examenes
    ], use_container_width=True, hide_index=True)

    pestaña_carga, pestaña_consulta, pestaña_correccion = st.tabs([
        '📤 Cargar resultados', '📄 Consultar archivos', '✏️ Corregir asociación'
    ])

    with pestaña_carga:
        st.write('Seleccioná uno o varios exámenes. Cada archivo se asociará a todos los exámenes seleccionados.')
        opciones_examenes = {etiqueta_examen(e): e['ID_Examen'] for e in examenes}
        with st.form(f'form_cargar_resultados_{id_boleta}', clear_on_submit=True):
            seleccionados = st.multiselect('Exámenes incluidos en los documentos *', list(opciones_examenes))
            archivos = st.file_uploader(
                'Archivos de resultados * (PDF o imágenes)',
                type=['pdf', 'jpg', 'jpeg', 'png'], accept_multiple_files=True,
                help='Máximo 10 MB por archivo. Podés cargar varios archivos para un mismo examen.'
            )
            fecha_realizacion = st.date_input('Fecha de realización de los exámenes', value=date.today())
            enviar = st.form_submit_button('💾 Guardar resultados', use_container_width=True)
        if enviar:
            if not seleccionados:
                st.error('Seleccioná al menos un examen.')
            elif not archivos:
                st.error('Adjuntá al menos un archivo.')
            else:
                ids = [opciones_examenes[etiqueta] for etiqueta in seleccionados]
                correcto, mensaje = guardar_resultados(id_boleta, ids, archivos, id_usuario, fecha_realizacion)
                if correcto:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(f'No se pudieron guardar los resultados: {mensaje}')

    with pestaña_consulta:
        try:
            asociados = consultar('''
                SELECT E.ID_Examen, T.Nombre AS Examen, A.ID_Archivo,
                       A.Nombre_Archivo, A.Ruta_Archivo, A.Tipo_Archivo,
                       A.Fecha_Carga, A.ID_User
                FROM Examen E
                JOIN Tipo_Examen T ON T.ID_TipoExamen = E.ID_TipoExamen
                JOIN Examen_Archivo EA ON EA.ID_Examen = E.ID_Examen
                JOIN Archivo_Resultado A ON A.ID_Archivo = EA.ID_Archivo
                WHERE E.ID_Boleta = %s
                ORDER BY E.ID_Examen, A.Fecha_Carga DESC, A.ID_Archivo DESC
            ''', (id_boleta,))
            if not asociados:
                st.info('Todavía no hay resultados cargados para esta boleta.')
            for item in asociados:
                with st.expander(f"{item['Examen']} — {item['Nombre_Archivo']} (archivo #{item['ID_Archivo']})"):
                    st.caption(f"Cargado: {item['Fecha_Carga']} | Usuario ID: {item['ID_User']}")
                    ruta = Path(item['Ruta_Archivo'])
                    if not ruta.is_file():
                        st.warning('El archivo ya no está disponible en el almacenamiento de Streamlit.')
                        continue
                    contenido = ruta.read_bytes()
                    st.download_button(
                        '📥 Descargar archivo', data=contenido,
                        file_name=item['Nombre_Archivo'], mime=item['Tipo_Archivo'],
                        key=f"descargar_{id_boleta}_{item['ID_Examen']}_{item['ID_Archivo']}"
                    )
                    if item['Tipo_Archivo'].startswith('image/'):
                        st.image(contenido, use_container_width=True)
        except Exception as error:
            st.error(f'No se pudieron consultar los archivos: {error}')

    with pestaña_correccion:
        st.warning('Esta opción retira el documento de un examen, pero no lo borra de otros exámenes que lo compartan.')
        try:
            asociaciones = consultar('''
                SELECT E.ID_Examen, T.Nombre AS Examen,
                       A.ID_Archivo, A.Nombre_Archivo
                FROM Examen E
                JOIN Tipo_Examen T ON T.ID_TipoExamen = E.ID_TipoExamen
                JOIN Examen_Archivo EA ON EA.ID_Examen = E.ID_Examen
                JOIN Archivo_Resultado A ON A.ID_Archivo = EA.ID_Archivo
                WHERE E.ID_Boleta = %s
                ORDER BY E.ID_Examen, A.ID_Archivo
            ''', (id_boleta,))
            if asociaciones:
                opciones = {
                    f"{a['Examen']} (examen #{a['ID_Examen']}) — {a['Nombre_Archivo']} (archivo #{a['ID_Archivo']})":
                    (a['ID_Examen'], a['ID_Archivo'])
                    for a in asociaciones
                }
                with st.form(f'form_correccion_{id_boleta}'):
                    seleccion_asociacion = st.selectbox('Asociación que querés retirar', list(opciones))
                    confirmar = st.checkbox('Confirmo que esta asociación es incorrecta')
                    retirar = st.form_submit_button('Retirar asociación')
                if retirar:
                    if not confirmar:
                        st.error('Marcá la confirmación para continuar.')
                    else:
                        correcto, mensaje = quitar_asociacion(*opciones[seleccion_asociacion])
                        if correcto:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
            else:
                st.info('No hay asociaciones para corregir.')
        except Exception as error:
            st.error(f'No se pudieron cargar las asociaciones: {error}')

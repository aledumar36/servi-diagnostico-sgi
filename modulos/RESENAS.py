"""Reseñas: escritura exclusiva del paciente y consulta del administrador."""
import streamlit as st
from config.conexion import obtener_conexion


def _usuario_y_rol():
    usuario = st.session_state.get('usuario')
    if not st.session_state.get('autenticado') or not isinstance(usuario, dict):
        return None, ''
    return usuario, str(usuario.get('Rol', '')).strip().lower()


def mostrar_resenas_paciente():
    usuario, rol = _usuario_y_rol()
    if rol != 'paciente' or not usuario or not usuario.get('ID_Paciente'):
        st.error('Esta función es exclusiva de pacientes con una cuenta vinculada.')
        return
    id_paciente = usuario['ID_Paciente']
    st.subheader('⭐ Mi experiencia en Servi-Diagnóstico')
    st.caption('Podés dejar una calificación y un comentario sobre la atención recibida.')
    with st.form('form_resena_paciente', clear_on_submit=True):
        calificacion = st.select_slider('Calificación', options=[1, 2, 3, 4, 5], value=5,
                                         format_func=lambda n: f'{n} estrella' if n == 1 else f'{n} estrellas')
        comentario = st.text_area('Comentario (opcional)', max_chars=1500)
        enviar = st.form_submit_button('Enviar reseña')
    if enviar:
        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute('''INSERT INTO Resena (ID_Paciente, Calificacion, Comentario)
                              VALUES (%s, %s, %s)''',
                           (id_paciente, calificacion, comentario.strip() or None))
            conexion.commit()
            st.success('¡Gracias! Tu reseña se registró correctamente.')
        except Exception:
            if conexion:
                conexion.rollback()
            st.error('No se pudo registrar la reseña. Intentá nuevamente.')
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute('''SELECT ID_Resena, Calificacion, Comentario, Fecha
                          FROM Resena WHERE ID_Paciente=%s
                          ORDER BY Fecha DESC, ID_Resena DESC''', (id_paciente,))
        registros = cursor.fetchall()
        st.markdown('**Mis reseñas anteriores**')
        if not registros:
            st.info('Todavía no has enviado reseñas.')
        for r in registros:
            with st.container(border=True):
                st.write(f"{'⭐' * int(r['Calificacion'] or 0)} · {r['Fecha']}")
                st.write(r['Comentario'] or 'Sin comentario')
    except Exception:
        st.warning('No se pudo cargar el historial de reseñas.')
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


def mostrar_resenas_admin():
    usuario, rol = _usuario_y_rol()
    if rol != 'regente-administrador':
        st.error('Solo el regente-administrador puede consultar todas las reseñas.')
        return
    st.title('⭐ Reseñas de pacientes')
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute('''SELECT R.ID_Resena, P.Nombre_Completo, R.Calificacion,
                                 R.Comentario, R.Fecha
                          FROM Resena R
                          INNER JOIN Paciente P ON P.ID_Paciente=R.ID_Paciente
                          ORDER BY R.Fecha DESC, R.ID_Resena DESC''')
        registros = cursor.fetchall()
        if not registros:
            st.info('Todavía no hay reseñas registradas.')
            return
        validas = [int(r['Calificacion']) for r in registros if r['Calificacion'] is not None]
        c1, c2 = st.columns(2)
        c1.metric('Reseñas recibidas', len(registros))
        c2.metric('Calificación promedio', f'{sum(validas) / len(validas):.1f} / 5' if validas else 'Sin calificaciones')
        st.dataframe([{
            'Fecha': r['Fecha'], 'Paciente': r['Nombre_Completo'],
            'Calificación': r['Calificacion'], 'Comentario': r['Comentario'] or ''
        } for r in registros], use_container_width=True, hide_index=True)
    except Exception:
        st.error('No se pudieron consultar las reseñas.')
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

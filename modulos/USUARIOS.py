import streamlit as st
from config.conexion import obtener_conexion
from modulos.SEGURIDAD import crear_hash

ROLES = {1: 'Regente-administrador', 2: 'Secretario', 3: 'Medico', 4: 'Paciente'}


def mostrar_usuarios():
    usuario_actual = st.session_state.get('usuario') or {}
    if str(usuario_actual.get('Rol', '')).strip().lower() != 'regente-administrador':
        st.error('Solo el regente-administrador puede gestionar usuarios.')
        return

    st.title('👥 Usuarios y roles')
    st.caption('Crear cuentas, consultar usuarios, cambiar su estado y restablecer contraseñas.')
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute('SELECT ID_Medico, Nombre, Apellido FROM Medico ORDER BY Nombre, Apellido')
        medicos = cursor.fetchall()
        cursor.execute('SELECT ID_Paciente, Nombre_Completo FROM Paciente ORDER BY Nombre_Completo')
        pacientes = cursor.fetchall()
        cursor.execute('''SELECT U.ID_User, U.Nombre, U.Apellido, U.Usuario, U.Estado,
                          U.ID_Rol, U.ID_Medico, U.ID_Paciente, R.Nombre AS Rol
                          FROM Usuario_Sistema U JOIN Rol R ON U.ID_Rol=R.ID_Rol
                          ORDER BY U.ID_User''')
        usuarios = cursor.fetchall()

        tab1, tab2, tab3 = st.tabs(['Registrar usuario', 'Consultar y activar/desactivar', 'Restablecer contraseña'])
        with tab1:
            rol = st.selectbox('Rol *', list(ROLES), format_func=lambda x: ROLES[x], key='rol_nuevo_usuario')
            with st.form('crear_usuario'):
                nombre = st.text_input('Nombre *')
                apellido = st.text_input('Apellido *')
                cuenta = st.text_input('Nombre de usuario *')
                clave = st.text_input('Contraseña inicial (mínimo 10 caracteres) *', type='password')
                repetir = st.text_input('Confirmar contraseña *', type='password')
                opciones_medico = {'Sin vincular': None}
                opciones_medico.update({f"#{m['ID_Medico']} - {m['Nombre']} {m['Apellido']}": m['ID_Medico'] for m in medicos})
                opciones_paciente = {'Sin vincular': None}
                opciones_paciente.update({f"#{p['ID_Paciente']} - {p['Nombre_Completo']}": p['ID_Paciente'] for p in pacientes})
                medico = st.selectbox('Médico vinculado (solo para rol Médico)', list(opciones_medico)) if rol == 3 else None
                paciente = st.selectbox('Paciente vinculado (solo para rol Paciente)', list(opciones_paciente)) if rol == 4 else None
                enviar = st.form_submit_button('Crear cuenta', type='primary')
            if enviar:
                id_medico = opciones_medico[medico] if rol == 3 else None
                id_paciente = opciones_paciente[paciente] if rol == 4 else None
                if not all([nombre.strip(), apellido.strip(), cuenta.strip(), clave]):
                    st.warning('Completá todos los campos obligatorios.')
                elif clave != repetir:
                    st.warning('Las contraseñas no coinciden.')
                elif (rol == 3 and id_medico is None) or (rol == 4 and id_paciente is None):
                    st.warning('Debés vincular la cuenta con el médico o paciente correspondiente.')
                else:
                    hash_clave = crear_hash(clave)
                    cursor.execute('''INSERT INTO Usuario_Sistema
                        (ID_Rol, ID_Medico, ID_Paciente, Nombre, Apellido, Usuario, Contrasena, Estado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')''',
                        (rol, id_medico, id_paciente, nombre.strip(), apellido.strip(), cuenta.strip(), hash_clave))
                    conexion.commit()
                    st.success('Cuenta creada correctamente. La contraseña no se muestra ni se almacena en texto plano.')

        with tab2:
            if usuarios:
                st.dataframe([{'ID': u['ID_User'], 'Nombre': f"{u['Nombre']} {u['Apellido']}",
                              'Usuario': u['Usuario'], 'Rol': u['Rol'], 'Estado': u['Estado']}
                              for u in usuarios], hide_index=True, use_container_width=True)
                opciones = {f"#{u['ID_User']} - {u['Usuario']} ({u['Rol']})": u for u in usuarios}
                elegido = st.selectbox('Cuenta', list(opciones), key='usuario_estado')
                actual = opciones[elegido]
                nuevo_estado = st.selectbox('Nuevo estado', ['Activo', 'Inactivo'],
                                            index=0 if actual['Estado'] == 'Activo' else 1)
                if st.button('Guardar estado'):
                    if actual['ID_User'] == usuario_actual.get('ID_User') and nuevo_estado == 'Inactivo':
                        st.error('No podés desactivar tu propia cuenta.')
                    else:
                        cursor.execute('UPDATE Usuario_Sistema SET Estado=%s WHERE ID_User=%s',
                                       (nuevo_estado, actual['ID_User']))
                        conexion.commit()
                        st.success('Estado actualizado. Volvé a abrir el módulo para ver el cambio.')
            else:
                st.info('No hay usuarios registrados.')

        with tab3:
            if usuarios:
                opciones = {f"#{u['ID_User']} - {u['Usuario']}": u for u in usuarios}
                with st.form('reiniciar_clave'):
                    elegido = st.selectbox('Cuenta a restablecer', list(opciones))
                    nueva = st.text_input('Nueva contraseña (mínimo 10 caracteres)', type='password')
                    confirmar = st.text_input('Confirmar nueva contraseña', type='password')
                    guardar = st.form_submit_button('Restablecer contraseña')
                if guardar:
                    if nueva != confirmar:
                        st.warning('Las contraseñas no coinciden.')
                    else:
                        nuevo_hash = crear_hash(nueva)
                        cursor.execute('UPDATE Usuario_Sistema SET Contrasena=%s WHERE ID_User=%s',
                                       (nuevo_hash, opciones[elegido]['ID_User']))
                        conexion.commit()
                        st.success('Contraseña restablecida correctamente.')
    except ValueError as e:
        if conexion:
            conexion.rollback()
        st.warning(str(e))
    except Exception as e:
        if conexion:
            conexion.rollback()
        st.error(f'No se pudo completar la operación: {e}')
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

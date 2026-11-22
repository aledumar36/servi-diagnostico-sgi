"""Órdenes de compra de Servi-Diagnóstico (prototipo)."""
from datetime import date
from decimal import Decimal
import streamlit as st
from config.conexion import obtener_conexion


def _leer(sql, params=()):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


def mostrar_compras():
    usuario = st.session_state.get('usuario', {})
    if (not st.session_state.get('autenticado') or
            str(usuario.get('Rol', '')).strip().lower() != 'regente-administrador'):
        st.error('Acceso exclusivo del regente-administrador.')
        return
    id_user = usuario.get('ID_User')
    if not id_user:
        st.error('No se pudo identificar el usuario.')
        return

    st.title('🛒 Órdenes de compra')
    st.caption('Registrar una orden NO modifica las existencias del inventario.')
    try:
        proveedores = _leer('SELECT ID_Proveedor, Nombre_Completo FROM Proveedor ORDER BY Nombre_Completo')
        productos = _leer('SELECT ID_Producto, Nombre, Marca FROM Producto ORDER BY Nombre, ID_Producto')
    except Exception as error:
        st.error(f'No se pudieron cargar los catálogos: {error}')
        return

    tab_registro, tab_historial = st.tabs(['Registrar orden', 'Consultar órdenes'])
    with tab_registro:
        if not proveedores or not productos:
            st.warning('Registrá al menos un proveedor y un producto antes de crear órdenes.')
        else:
            opciones_proveedor = {f"{p['Nombre_Completo']} (#{p['ID_Proveedor']})": p['ID_Proveedor'] for p in proveedores}
            opciones_producto = {f"{p['Nombre']} · {p['Marca'] or 'Sin marca'} (#{p['ID_Producto']})": p['ID_Producto'] for p in productos}
            st.write('Agregá los productos de la orden y sus precios unitarios.')
            cantidad_lineas = st.number_input('Número de productos diferentes', min_value=1, max_value=15, value=1, step=1, key='compras_num_lineas')
            with st.form('registrar_orden_compra'):
                proveedor = st.selectbox('Proveedor *', list(opciones_proveedor))
                concepto = st.text_input('Concepto (opcional)', max_chars=255)
                fecha_pedido = st.date_input('Fecha del pedido', value=date.today())
                fecha_entrega = st.date_input(
                    'Fecha estimada de entrega (opcional)',
                    value=None,
                    min_value=fecha_pedido,
                    format='DD/MM/YYYY'
                    )
                lineas = []
                for i in range(int(cantidad_lineas)):
                    st.markdown(f'**Producto {i+1}**')
                    col_p, col_c, col_u = st.columns([3, 1, 1])
                    with col_p:
                        etiqueta = st.selectbox('Producto', list(opciones_producto), key=f'compra_prod_{i}')
                    with col_c:
                        cantidad = st.number_input('Cantidad', min_value=0.01, value=1.0, step=1.0, format='%.2f', key=f'compra_cant_{i}')
                    with col_u:
                        precio = st.number_input('Precio unitario ($)', min_value=0.0, value=0.0, step=0.01, format='%.2f', key=f'compra_precio_{i}')
                    lineas.append((opciones_producto[etiqueta], Decimal(str(cantidad)), Decimal(str(precio))))
                confirmar = st.checkbox('Confirmo que los datos de la orden son correctos')
                guardar = st.form_submit_button('💾 Registrar orden de compra', use_container_width=True)

            if guardar:
                ids = [linea[0] for linea in lineas]
                if not confirmar:
                    st.error('Confirmá los datos antes de guardar.')
                elif len(ids) != len(set(ids)):
                    st.error('No repitás un producto en varias líneas; agrupá su cantidad.')
                elif fecha_entrega and fecha_entrega < fecha_pedido:
                    st.error('La fecha estimada de entrega no puede ser anterior al pedido.')
                else:
                    total = sum((c * p for _, c, p in lineas), Decimal('0')).quantize(Decimal('0.01'))
                    conexion = None
                    cursor = None
                    try:
                        conexion = obtener_conexion()
                        cursor = conexion.cursor()
                        conexion.start_transaction()
                        cursor.execute('''INSERT INTO Orden_Compra
                            (ID_Proveedor, ID_User, Concepto, Fecha_Pedido, Fecha_Entrega, Total)
                            VALUES (%s, %s, %s, %s, %s, %s)''',
                            (opciones_proveedor[proveedor], id_user, concepto.strip() or None,
                             fecha_pedido, fecha_entrega, total))
                        id_compra = cursor.lastrowid
                        cursor.executemany('''INSERT INTO Detalle_Compra
                            (ID_Compra, ID_Producto, Cantidad, Precio_Unitario)
                            VALUES (%s, %s, %s, %s)''',
                            [(id_compra, id_producto, cantidad, precio) for id_producto, cantidad, precio in lineas])
                        conexion.commit()
                        st.success(f'Orden #{id_compra} registrada correctamente. Total: ${total:,.2f}. El inventario no se modificó.')
                    except Exception as error:
                        if conexion:
                            conexion.rollback()
                        st.error(f'No se pudo guardar la orden: {error}')
                    finally:
                        if cursor:
                            cursor.close()
                        if conexion:
                            conexion.close()

    with tab_historial:
        try:
            ordenes = _leer('''SELECT O.ID_Compra, P.Nombre_Completo AS Proveedor,
                O.Concepto, O.Fecha_Pedido, O.Fecha_Entrega, O.Total
                FROM Orden_Compra O JOIN Proveedor P ON P.ID_Proveedor=O.ID_Proveedor
                ORDER BY O.ID_Compra DESC''')
            if not ordenes:
                st.info('Todavía no hay órdenes registradas.')
            else:
                st.dataframe(ordenes, use_container_width=True, hide_index=True)
                etiquetas = {f"Orden #{o['ID_Compra']} · {o['Proveedor']}": o['ID_Compra'] for o in ordenes}
                elegida = st.selectbox('Ver detalle de la orden', list(etiquetas))
                detalles = _leer('''SELECT P.Nombre AS Producto, D.Cantidad, D.Precio_Unitario,
                    (D.Cantidad * D.Precio_Unitario) AS Subtotal
                    FROM Detalle_Compra D JOIN Producto P ON P.ID_Producto=D.ID_Producto
                    WHERE D.ID_Compra=%s ORDER BY D.ID_DetalleCompra''', (etiquetas[elegida],))
                st.dataframe(detalles, use_container_width=True, hide_index=True)
        except Exception as error:
            st.error(f'No se pudieron consultar las órdenes: {error}')

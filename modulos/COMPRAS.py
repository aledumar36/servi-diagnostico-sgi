"""Órdenes de compra de Servi-Diagnóstico (prototipo)."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
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

    tab_registro, tab_historial, tab_recepcion = st.tabs(['Registrar orden', 'Consultar órdenes', 'Recepción de compras'])
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
                fecha_entrega = st.date_input('Fecha estimada de entrega (opcional)', value=None, min_value=fecha_pedido, format='DD/MM/YYYY')
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


    # ==========================================================
    # RECEPCIÓN PARCIAL O TOTAL DE PRODUCTOS
    # ==========================================================
    with tab_recepcion:
        st.subheader('📥 Recepción de compras')
        st.caption('Las existencias solo aumentan al confirmar una recepción. Podés recibir una orden en varias entregas.')
        try:
            pendientes = _leer("""
                SELECT O.ID_Compra, O.Fecha_Pedido, P.Nombre_Completo AS Proveedor,
                       D.ID_DetalleCompra, D.ID_Producto, PR.Nombre AS Producto,
                       D.Cantidad AS Pedida,
                       COALESCE((SELECT SUM(M.Cantidad)
                                 FROM Inventario I
                                 JOIN Movimiento_Inventario M ON M.ID_Inventario = I.ID_Inventario
                                 WHERE I.ID_DetalleCompra = D.ID_DetalleCompra
                                   AND M.Tipo_Movimiento = 'Entrada'), 0) AS Recibida
                FROM Orden_Compra O
                JOIN Proveedor P ON P.ID_Proveedor = O.ID_Proveedor
                JOIN Detalle_Compra D ON D.ID_Compra = O.ID_Compra
                JOIN Producto PR ON PR.ID_Producto = D.ID_Producto
                ORDER BY O.ID_Compra DESC, D.ID_DetalleCompra
            """)
        except Exception as error:
            st.error(f'No se pudieron consultar las compras: {error}')
            return

        if not pendientes:
            st.info('Todavía no hay órdenes de compra.')
        else:
            por_orden = {}
            for item in pendientes:
                por_orden.setdefault(item['ID_Compra'], []).append(item)
            etiquetas = {
                f"Orden #{id_compra} · {items[0]['Proveedor']}": id_compra
                for id_compra, items in por_orden.items()
            }
            orden_elegida = st.selectbox('Seleccionar orden de compra', list(etiquetas), key='recepcion_orden')
            id_compra = etiquetas[orden_elegida]
            detalles = por_orden[id_compra]
            filas = []
            for item in detalles:
                pedida = Decimal(str(item['Pedida']))
                recibida = Decimal(str(item['Recibida']))
                faltante = max(Decimal('0'), pedida - recibida)
                filas.append({
                    'Producto': item['Producto'], 'Pedido': float(pedida),
                    'Recibido': float(recibida), 'Pendiente': float(faltante)
                })
            st.dataframe(filas, use_container_width=True, hide_index=True)

            disponibles = [i for i in detalles if Decimal(str(i['Pedida'])) > Decimal(str(i['Recibida']))]
            if not disponibles:
                st.success('Esta orden ya está recibida completamente.')
            else:
                opciones = {
                    f"{i['Producto']} · Pendiente: {Decimal(str(i['Pedida'])) - Decimal(str(i['Recibida'])):.2f}": i['ID_DetalleCompra']
                    for i in disponibles
                }
                with st.form('form_recepcion_compra'):
                    producto_seleccionado = st.selectbox('Producto que llegó', list(opciones))
                    cantidad = st.number_input('Cantidad recibida', min_value=0.01, value=1.0, step=1.0, format='%.2f')
                    fecha_recepcion = st.date_input('Fecha de recepción / almacenamiento', value=date.today())
                    fecha_vencimiento = st.date_input('Fecha de vencimiento (opcional)', value=None, format='DD/MM/YYYY')
                    stock_minimo = st.number_input('Stock mínimo para este lote', min_value=0.0, value=0.0, step=1.0, format='%.2f')
                    confirmar_recepcion = st.checkbox('Confirmo que esta cantidad fue recibida físicamente')
                    guardar_recepcion = st.form_submit_button('📦 Registrar recepción', use_container_width=True)

                if guardar_recepcion:
                    id_detalle = opciones[producto_seleccionado]
                    cantidad_decimal = Decimal(str(cantidad)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    if not confirmar_recepcion:
                        st.error('Confirmá la recepción física del producto.')
                    elif fecha_vencimiento and fecha_vencimiento < fecha_recepcion:
                        st.error('El vencimiento no puede ser anterior a la fecha de recepción.')
                    else:
                        conexion = None
                        cursor = None
                        try:
                            conexion = obtener_conexion()
                            cursor = conexion.cursor(dictionary=True)
                            conexion.start_transaction()
                            # Bloquear el detalle impide que dos recepciones simultáneas
                            # superen la cantidad pedida.
                            cursor.execute("""
                                SELECT ID_Producto, Cantidad FROM Detalle_Compra
                                WHERE ID_DetalleCompra = %s AND ID_Compra = %s FOR UPDATE
                            """, (id_detalle, id_compra))
                            detalle = cursor.fetchone()
                            if not detalle:
                                raise ValueError('El detalle de compra ya no existe.')
                            cursor.execute("""
                                SELECT COALESCE(SUM(M.Cantidad), 0) AS Recibido
                                FROM Inventario I
                                JOIN Movimiento_Inventario M ON M.ID_Inventario = I.ID_Inventario
                                WHERE I.ID_DetalleCompra = %s
                                  AND M.Tipo_Movimiento = 'Entrada'
                            """, (id_detalle,))
                            recibido = Decimal(str(cursor.fetchone()['Recibido']))
                            pedido = Decimal(str(detalle['Cantidad']))
                            faltante = pedido - recibido
                            if cantidad_decimal <= 0 or cantidad_decimal > faltante:
                                raise ValueError(f'La cantidad supera lo pendiente ({faltante:.2f}). Actualizá la página y verificá.')
                            cursor.execute("""
                                INSERT INTO Inventario
                                  (ID_Producto, ID_User, ID_DetalleCompra, Fecha_Almacenado,
                                   Fecha_Vencimiento, Stock_Minimo, Cantidad)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (detalle['ID_Producto'], id_user, id_detalle,
                                  fecha_recepcion, fecha_vencimiento, Decimal(str(stock_minimo)), cantidad_decimal))
                            id_inventario = cursor.lastrowid
                            cursor.execute("""
                                INSERT INTO Movimiento_Inventario
                                  (ID_Inventario, ID_User, Tipo_Movimiento, Cantidad, Motivo)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (id_inventario, id_user, 'Entrada', cantidad_decimal,
                                  f'Recepción de orden de compra #{id_compra}'))
                            conexion.commit()
                            st.success(f'Recepción registrada: {cantidad_decimal:.2f} unidades. Pendientes: {faltante-cantidad_decimal:.2f}.')
                            st.rerun()
                        except Exception as error:
                            if conexion:
                                conexion.rollback()
                            st.error(f'No se pudo registrar la recepción: {error}')
                        finally:
                            if cursor:
                                cursor.close()
                            if conexion:
                                conexion.close()

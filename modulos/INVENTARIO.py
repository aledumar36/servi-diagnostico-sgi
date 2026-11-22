import streamlit as st
from datetime import date
from config.conexion import obtener_conexion


def mostrar_inventario():

    st.title("📦 Gestión de inventario")
    st.write(
        "Control de existencias, vencimientos "
        "y movimientos de productos."
    )

    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Consultar inventario",
        "Registrar producto",
        "Registrar entrada",
        "Registrar salida",
        "Editar inventario",
        "Historial de movimientos"
    ])

    # ==========================================
    # CONSULTAR INVENTARIO
    # ==========================================

    with tab1:

        st.subheader("Existencias disponibles")

        conexion = None
        cursor = None

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    I.ID_Inventario,
                    P.Nombre AS Producto,
                    P.Marca,
                    P.Area,
                    I.Cantidad,
                    I.Stock_Minimo,
                    I.Fecha_Vencimiento
                FROM Inventario I
                INNER JOIN Producto P
                    ON I.ID_Producto = P.ID_Producto
                ORDER BY P.Nombre
            """)

            inventario = cursor.fetchall()

            if inventario:

                st.dataframe(
                    inventario,
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Alertas")

                for item in inventario:

                    if item["Cantidad"] <= item["Stock_Minimo"]:
                        st.warning(
                            f"Stock bajo: {item['Producto']}"
                        )

                    vencimiento = item["Fecha_Vencimiento"]

                    if vencimiento:

                        if vencimiento < date.today():
                            st.error(
                                f"Producto vencido: {item['Producto']}"
                            )

            else:
                st.info(
                    "Todavía no hay existencias "
                    "registradas en inventario."
                )

        except Exception as e:
            st.error(f"Error al consultar inventario: {e}")

        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    # ==========================================
    # REGISTRAR PRODUCTO
    # ==========================================

    with tab2:

        st.subheader("Registrar nuevo producto")

        conexion = None
        cursor = None

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT ID_Proveedor, Nombre_Completo
                FROM Proveedor
                ORDER BY Nombre_Completo
            """)

            proveedores = cursor.fetchall()

            if not proveedores:

                st.warning(
                    "Primero debe registrar un proveedor."
                )

            else:

                opciones_proveedores = {
                    f"{p['ID_Proveedor']} - {p['Nombre_Completo']}":
                    p["ID_Proveedor"]
                    for p in proveedores
                }

                with st.form("form_producto"):

                    nombre = st.text_input(
                        "Nombre del producto *"
                    )

                    marca = st.text_input("Marca")

                    descripcion = st.text_area(
                        "Descripción"
                    )

                    area = st.selectbox(
                        "Área",
                        [
                            "Hematología",
                            "Química sanguínea",
                            "Uroanálisis",
                            "Coprología",
                            "Microbiología",
                            "Insumos generales",
                            "Otros"
                        ]
                    )

                    proveedor = st.selectbox(
                        "Proveedor",
                        list(opciones_proveedores.keys())
                    )

                    guardar = st.form_submit_button(
                        "Guardar producto"
                    )

                    if guardar:

                        if not nombre.strip():

                            st.warning(
                                "Ingrese el nombre del producto."
                            )

                        else:

                            cursor.execute("""
                                INSERT INTO Producto
                                (
                                    ID_Proveedor,
                                    Nombre,
                                    Marca,
                                    Descripcion,
                                    Area
                                )
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                opciones_proveedores[proveedor],
                                nombre.strip(),
                                marca.strip(),
                                descripcion.strip(),
                                area
                            ))

                            conexion.commit()

                            st.success(
                                "Producto registrado correctamente."
                            )

        except Exception as e:

            if conexion:
                conexion.rollback()

            st.error(
                f"Error al registrar producto: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

    # ==========================================
    # REGISTRAR ENTRADA
    # ==========================================

    
    with tab3:

        st.subheader("Registrar entrada de producto")

        conexion = None
        cursor = None

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT ID_Producto, Nombre, Marca
                FROM Producto
                ORDER BY Nombre
            """)

            productos = cursor.fetchall()

            if not productos:
                st.warning(
                    "Primero debe registrar un producto."
                )

            else:

                opciones_productos = {
                    f"{p['ID_Producto']} - {p['Nombre']} ({p['Marca'] or 'Sin marca'})":
                    p["ID_Producto"]
                    for p in productos
                }

                with st.form("form_entrada_inventario"):

                    producto = st.selectbox(
                        "Producto *",
                        list(opciones_productos.keys())
                    )

                    cantidad = st.number_input(
                        "Cantidad recibida *",
                        min_value=1.0,
                        step=1.0
                    )

                    stock_minimo = st.number_input(
                        "Stock mínimo",
                        min_value=0.0,
                        step=1.0
                    )

                    fecha_almacenado = st.date_input(
                        "Fecha de almacenamiento",
                        value=date.today()
                    )


                    tiene_vencimiento = st.checkbox(
                        "El producto tiene fecha de vencimiento",
                        value=True
                    )

                    fecha_vencimiento = st.date_input(
                        "Fecha de vencimiento",
                        value=date.today(),
                        min_value=date(2000, 1, 1),
                        max_value=date(2100, 12, 31),
                        disabled=not tiene_vencimiento
                    )

                    if not tiene_vencimiento:
                        fecha_vencimiento = None

                    motivo = st.text_input(
                        "Motivo de entrada",
                        value="Ingreso de producto"
                    )

                    guardar_entrada = st.form_submit_button(
                        "Guardar entrada"
                    )

                if guardar_entrada:

                    if (
                        fecha_vencimiento is not None
                        and fecha_vencimiento < fecha_almacenado
                    ):
                        st.warning(
                            "La fecha de vencimiento no puede "
                            "ser anterior a la de almacenamiento."
                        )

                    else:

                        id_producto = opciones_productos[producto]

                        usuario = st.session_state.get("usuario")

                        if not usuario or not usuario.get("ID_User"):
                            st.error(
                                "No se encontró el usuario activo."
                            )

                        else:

                            id_usuario = usuario["ID_User"]

                            cursor.execute("""
                                INSERT INTO Inventario
                                (
                                    ID_Producto,
                                    ID_User,
                                    Fecha_Almacenado,
                                    Fecha_Vencimiento,
                                    Stock_Minimo,
                                    Cantidad
                                )
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                id_producto,
                                id_usuario,
                                fecha_almacenado,
                                fecha_vencimiento,
                                stock_minimo,
                                cantidad
                            ))

                            id_inventario = cursor.lastrowid

                            cursor.execute("""
                                INSERT INTO Movimiento_Inventario
                                (
                                    ID_Inventario,
                                    ID_User,
                                    Tipo_Movimiento,
                                    Cantidad,
                                    Motivo
                                )
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                id_inventario,
                                id_usuario,
                                "Entrada",
                                cantidad,
                                motivo.strip() or "Ingreso de producto"
                            ))

                            conexion.commit()

                            st.success(
                                "Entrada registrada correctamente."
                            )

        except Exception as e:

            if conexion:
                conexion.rollback()

            st.error(
                f"Error al registrar entrada: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

    # ==========================================
    # REGISTRAR SALIDA DE INVENTARIO
    # ==========================================

    with tab4:

        st.subheader("Registrar salida de producto")

        st.write(
            "Registre los materiales o reactivos "
            "retirados del inventario."
        )

        conexion = None
        cursor = None

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    I.ID_Inventario,
                    P.Nombre AS Producto,
                    P.Marca,
                    I.Cantidad,
                    I.Fecha_Vencimiento
                FROM Inventario I
                INNER JOIN Producto P
                    ON I.ID_Producto = P.ID_Producto
                WHERE I.Cantidad > 0
                ORDER BY P.Nombre, I.Fecha_Vencimiento
            """)

            registros = cursor.fetchall()

            if not registros:

                st.info(
                    "No hay productos con existencias "
                    "disponibles para retirar."
                )

            else:

                opciones = {}

                for r in registros:

                    vencimiento = (
                        str(r["Fecha_Vencimiento"])
                        if r["Fecha_Vencimiento"]
                        else "Sin vencimiento"
                    )

                    etiqueta = (
                        f"#{r['ID_Inventario']} - "
                        f"{r['Producto']} "
                        f"({r['Marca'] or 'Sin marca'}) | "
                        f"Disponible: {r['Cantidad']} | "
                        f"Vence: {vencimiento}"
                    )

                    opciones[etiqueta] = r

                with st.form("form_salida_inventario"):

                    seleccionado = st.selectbox(
                        "Seleccione el producto *",
                        list(opciones.keys())
                    )

                    registro = opciones[seleccionado]

                    st.info(
                        f"Cantidad disponible: "
                        f"{registro['Cantidad']}"
                    )

                    cantidad_salida = st.number_input(
                        "Cantidad a retirar *",
                        min_value=0.01,
                        step=1.0,
                        value=1.0
                    )

                    motivo = st.selectbox(
                        "Motivo de salida *",
                        [
                            "Uso en el laboratorio",
                            "Producto vencido",
                            "Producto dañado",
                            "Devolución",
                            "Otro"
                        ]
                    )

                    observaciones = st.text_area(
                        "Observaciones",
                        placeholder=(
                            "Ej. Material utilizado "
                            "en el área de hematología"
                        )
                    )

                    confirmar = st.checkbox(
                        "Confirmo que la cantidad "
                        "y el producto son correctos"
                    )

                    guardar_salida = st.form_submit_button(
                        "Registrar salida",
                        type="primary"
                    )

                if guardar_salida:

                    if not confirmar:

                        st.warning(
                            "Debe confirmar la salida."
                        )

                    else:

                        usuario = st.session_state.get(
                            "usuario", {}
                        )

                        id_usuario = usuario.get("ID_User")

                        if not id_usuario:

                            st.error(
                                "No se identificó al usuario."
                            )

                        else:

                            id_inventario = registro[
                                "ID_Inventario"
                            ]

                            # Bloquear registro para evitar
                            # retiros simultáneos incorrectos.
                            cursor.execute("""
                                SELECT Cantidad
                                FROM Inventario
                                WHERE ID_Inventario = %s
                                FOR UPDATE
                            """, (id_inventario,))

                            actual = cursor.fetchone()

                            if actual is None:

                                conexion.rollback()

                                st.error(
                                    "El registro de inventario "
                                    "ya no existe."
                                )

                            elif (
                                float(actual["Cantidad"])
                                < cantidad_salida
                            ):

                                conexion.rollback()

                                st.error(
                                    "La cantidad solicitada "
                                    "supera las existencias "
                                    "disponibles."
                                )

                            else:

                                cantidad_anterior = float(
                                    actual["Cantidad"]
                                )

                                nueva_cantidad = round(
                                    cantidad_anterior
                                    - cantidad_salida,
                                    2
                                )

                                cursor.execute("""
                                    UPDATE Inventario
                                    SET Cantidad = %s
                                    WHERE ID_Inventario = %s
                                """, (
                                    nueva_cantidad,
                                    id_inventario
                                ))

                                descripcion = motivo

                                if observaciones.strip():

                                    descripcion += (
                                        " | "
                                        + observaciones.strip()
                                    )

                                cursor.execute("""
                                    INSERT INTO
                                        Movimiento_Inventario
                                    (
                                        ID_Inventario,
                                        ID_User,
                                        Tipo_Movimiento,
                                        Cantidad,
                                        Motivo
                                    )
                                    VALUES (
                                        %s, %s, %s, %s, %s
                                    )
                                """, (
                                    id_inventario,
                                    id_usuario,
                                    "Salida",
                                    cantidad_salida,
                                    descripcion[:255]
                                ))

                                conexion.commit()

                                st.success(
                                    "Salida registrada "
                                    "correctamente."
                                )

                                st.write(
                                    f"Existencias anteriores: "
                                    f"{cantidad_anterior:g}"
                                )

                                st.write(
                                    f"Cantidad retirada: "
                                    f"{cantidad_salida:g}"
                                )

                                st.write(
                                    f"Existencias actuales: "
                                    f"{nueva_cantidad:g}"
                                )

        except Exception as e:

            if conexion:
                conexion.rollback()

            st.error(
                f"Error al registrar salida: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

    # ==========================================
    # EDITAR INVENTARIO
    # ==========================================

    with tab5:

        st.subheader("Editar inventario")
        st.write(
            "Corrija existencias, stock mínimo y "
            "fechas de vencimiento."
        )

        st.info(
            "Los cambios de cantidad se registrarán "
            "como movimientos de ajuste."
        )

        usuario = st.session_state.get("usuario", {})

        rol = str(usuario.get("Rol", "")).strip().lower()

        if rol != "regente-administrador":

            st.error(
                "Solo el regente-administrador puede "
                "realizar ajustes de inventario."
            )

        else:

            conexion = None
            cursor = None

            try:

                conexion = obtener_conexion()
                cursor = conexion.cursor(dictionary=True)

                cursor.execute("""
                    SELECT
                        I.ID_Inventario,
                        P.Nombre AS Producto,
                        P.Marca,
                        I.Cantidad,
                        I.Stock_Minimo,
                        I.Fecha_Almacenado,
                        I.Fecha_Vencimiento
                    FROM Inventario I
                    INNER JOIN Producto P
                        ON I.ID_Producto = P.ID_Producto
                    ORDER BY P.Nombre, I.ID_Inventario
                """)

                registros = cursor.fetchall()

                if not registros:

                    st.info(
                        "No hay existencias registradas "
                        "para modificar."
                    )

                else:

                    opciones = {
                        (
                            f"#{r['ID_Inventario']} - "
                            f"{r['Producto']} "
                            f"({r['Marca'] or 'Sin marca'})"
                        ): r
                        for r in registros
                    }

                    elegido = st.selectbox(
                        "Seleccione el registro de inventario",
                        list(opciones.keys())
                    )

                    registro = opciones[elegido]

                    id_inventario = registro["ID_Inventario"]

                    st.write(
                        f"**Cantidad actual:** "
                        f"{registro['Cantidad']}"
                    )

                    with st.form(
                        f"form_ajuste_{id_inventario}"
                    ):

                        nueva_cantidad = st.number_input(
                            "Nueva cantidad disponible",
                            min_value=0.0,
                            value=float(registro["Cantidad"]),
                            step=1.0
                        )

                        nuevo_stock_minimo = st.number_input(
                            "Stock mínimo",
                            min_value=0.0,
                            value=float(registro["Stock_Minimo"]),
                            step=1.0
                        )

                        fecha_almacenado = st.date_input(
                            "Fecha de almacenamiento",
                            value=registro["Fecha_Almacenado"],
                            min_value=date(2000, 1, 1),
                            max_value=date(2100, 12, 31)
                        )

                        tiene_vencimiento = st.checkbox(
                            "Tiene fecha de vencimiento",
                            value=(
                                registro["Fecha_Vencimiento"]
                                is not None
                            )
                        )

                        fecha_vencimiento = st.date_input(
                            "Fecha de vencimiento",
                            value=(
                                registro["Fecha_Vencimiento"]
                                or date.today()
                            ),
                            min_value=date(2000, 1, 1),
                            max_value=date(2100, 12, 31),
                            disabled=not tiene_vencimiento
                        )

                        if not tiene_vencimiento:
                            fecha_vencimiento = None

                        motivo = st.text_area(
                            "Motivo de la modificación *",
                            placeholder=(
                                "Ej. Corrección por conteo físico"
                            )
                        )

                        confirmar = st.checkbox(
                            "Confirmo que revisé los datos "
                            "y autorizo esta modificación"
                        )

                        guardar = st.form_submit_button(
                            "Guardar modificación",
                            type="primary"
                        )

                    if guardar:

                        if not motivo.strip():

                            st.warning(
                                "Debe indicar el motivo "
                                "de la modificación."
                            )

                        elif not confirmar:

                            st.warning(
                                "Debe confirmar la modificación."
                            )

                        elif (
                            fecha_vencimiento is not None
                            and fecha_vencimiento < fecha_almacenado
                        ):

                            st.warning(
                                "El vencimiento no puede ser "
                                "anterior al almacenamiento."
                            )

                        else:

                            cursor.execute("""
                                SELECT Cantidad
                                FROM Inventario
                                WHERE ID_Inventario = %s
                                FOR UPDATE
                            """, (id_inventario,))

                            actual = cursor.fetchone()

                            if actual is None:
                                conexion.rollback()
                                st.error(
                                    "El registro ya no existe."
                                )

                            else:

                                cantidad_anterior = float(
                                    actual["Cantidad"]
                                )

                                diferencia = round(
                                    nueva_cantidad - cantidad_anterior,
                                    2
                                )

                                cursor.execute("""
                                    UPDATE Inventario
                                    SET
                                        Cantidad = %s,
                                        Stock_Minimo = %s,
                                        Fecha_Almacenado = %s,
                                        Fecha_Vencimiento = %s
                                    WHERE ID_Inventario = %s
                                """, (
                                    nueva_cantidad,
                                    nuevo_stock_minimo,
                                    fecha_almacenado,
                                    fecha_vencimiento,
                                    id_inventario
                                ))

                                if diferencia != 0:

                                    id_usuario = usuario.get(
                                        "ID_User"
                                    )

                                    if not id_usuario:
                                        raise ValueError(
                                            "No se identificó "
                                            "al usuario activo."
                                        )

                                    descripcion = (
                                        f"{motivo.strip()} | "
                                        f"Anterior: "
                                        f"{cantidad_anterior:g} | "
                                        f"Nuevo: "
                                        f"{nueva_cantidad:g} | "
                                        f"Diferencia: "
                                        f"{diferencia:+g}"
                                    )

                                    cursor.execute("""
                                        INSERT INTO
                                            Movimiento_Inventario
                                        (
                                            ID_Inventario,
                                            ID_User,
                                            Tipo_Movimiento,
                                            Cantidad,
                                            Motivo
                                        )
                                        VALUES (
                                            %s, %s, %s, %s, %s
                                        )
                                    """, (
                                        id_inventario,
                                        id_usuario,
                                        "Ajuste",
                                        abs(diferencia),
                                        descripcion[:255]
                                    ))

                                conexion.commit()

                                st.success(
                                    "Inventario actualizado "
                                    "correctamente."
                                )

                                if diferencia != 0:

                                    st.info(
                                        f"Ajuste registrado: "
                                        f"{diferencia:+g} unidades."
                                    )

                                st.rerun()

            except Exception as e:

                if conexion:
                    conexion.rollback()

                st.error(
                    f"Error al editar inventario: {e}"
                )

            finally:

                if cursor:
                    cursor.close()

                if conexion:
                    conexion.close()


    # ==========================================
    # HISTORIAL DE MOVIMIENTOS
    # ==========================================

    with tab6:

        st.subheader("Historial de movimientos")

        st.write(
            "Consulta de entradas, salidas y ajustes "
            "realizados en el inventario."
        )

        conexion = None
        cursor = None

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    M.ID_Movimiento AS ID,
                    P.Nombre AS Producto,
                    P.Marca,
                    M.Tipo_Movimiento AS Movimiento,
                    M.Cantidad,
                    M.Fecha_Movimiento AS Fecha,
                    CONCAT(
                        U.Nombre, ' ', U.Apellido
                    ) AS Usuario,
                    M.Motivo,
                    M.ID_Inventario
                FROM Movimiento_Inventario M
                INNER JOIN Inventario I
                    ON M.ID_Inventario = I.ID_Inventario
                INNER JOIN Producto P
                    ON I.ID_Producto = P.ID_Producto
                INNER JOIN Usuario_Sistema U
                    ON M.ID_User = U.ID_User
                ORDER BY
                    M.Fecha_Movimiento DESC,
                    M.ID_Movimiento DESC
            """)

            movimientos = cursor.fetchall()

            if not movimientos:

                st.info(
                    "Todavía no hay movimientos registrados."
                )

            else:

                st.success(
                    f"Total de movimientos registrados: "
                    f"{len(movimientos)}"
                )

                tipos = [
                    "Todos",
                    "Entrada",
                    "Salida",
                    "Ajuste"
                ]

                filtro = st.selectbox(
                    "Filtrar por tipo de movimiento",
                    tipos
                )

                if filtro == "Todos":
                    filtrados = movimientos
                else:
                    filtrados = [
                        m for m in movimientos
                        if m["Movimiento"] == filtro
                    ]

                st.dataframe(
                    filtrados,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Los movimientos se muestran desde "
                    "el más reciente hasta el más antiguo."
                )

        except Exception as e:

            st.error(
                f"Error al consultar movimientos: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

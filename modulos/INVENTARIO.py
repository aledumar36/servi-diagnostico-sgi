import streamlit as st
from datetime import date
from config.conexion import obtener_conexion


def mostrar_inventario():

    st.title("📦 Gestión de inventario")
    st.write(
        "Control de existencias, vencimientos "
        "y movimientos de productos."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Consultar inventario",
        "Registrar producto",
        "Registrar entrada",
        "Registrar salida"
        "Editar inventario"
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
    # REGISTRAR SALIDA
    # ==========================================

    with tab4:

        st.subheader("Registrar salida de producto")

        st.info(
            "Aquí registraremos las salidas "
            "de productos del inventario."
        )


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


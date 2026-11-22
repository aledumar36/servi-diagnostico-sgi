import streamlit as st
from datetime import date
from config.conexion import obtener_conexion


def mostrar_inventario():

    st.title("📦 Gestión de inventario")
    st.write(
        "Control de existencias, vencimientos "
        "y movimientos de productos."
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Consultar inventario",
        "Registrar producto",
        "Registrar entrada",
        "Registrar salida"
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

        st.info(
            "Aquí registraremos las entradas "
            "de productos al inventario."
        )

    # ==========================================
    # REGISTRAR SALIDA
    # ==========================================

    with tab4:

        st.subheader("Registrar salida de producto")

        st.info(
            "Aquí registraremos las salidas "
            "de productos del inventario."
        )


import streamlit as st
from datetime import date
from config.conexion import obtener_conexion


def mostrar_inventario():

    st.title("📦 Gestión de inventario")
    st.write(
        "Control de existencias, vencimientos "
        "y movimientos de productos."
    )

    tab1, tab2, tab3 = st.tabs([
        "Consultar inventario",
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
                                f"Producto vencido: "
                                f"{item['Producto']}"
                            )

            else:
                st.info(
                    "Todavía no hay productos "
                    "registrados en inventario."
                )

        except Exception as e:
            st.error(f"Error al consultar inventario: {e}")

        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    # ==========================================
    # REGISTRAR ENTRADA
    # ==========================================

    with tab2:

        st.subheader("Registrar entrada de producto")

        st.info(
            "Aquí registraremos las entradas "
            "de productos al inventario."
        )

    # ==========================================
    # REGISTRAR SALIDA
    # ==========================================

    with tab3:

        st.subheader("Registrar salida de producto")

        st.info(
            "Aquí registraremos las salidas "
            "de productos del inventario."
        )

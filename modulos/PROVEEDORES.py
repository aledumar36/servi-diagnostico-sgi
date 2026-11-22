
import streamlit as st
from config.conexion import obtener_conexion


def mostrar_proveedores():

    st.title("🚚 Compras y proveedores")
    st.write("Gestión de proveedores de Servi-Diagnóstico.")

    tab1, tab2 = st.tabs([
        "Registrar proveedor",
        "Consultar proveedores"
    ])

    # ==========================================
    # REGISTRAR PROVEEDOR
    # ==========================================

    with tab1:

        st.subheader("Registrar nuevo proveedor")

        with st.form("form_proveedor"):

            nombre = st.text_input(
                "Nombre completo del proveedor *"
            )

            catalogo = st.text_area(
                "Catálogo de productos"
            )

            telefono = st.text_input(
                "Teléfono"
            )

            correo = st.text_input(
                "Correo electrónico"
            )

            guardar = st.form_submit_button(
                "Guardar proveedor"
            )

        if guardar:

            if not nombre.strip():

                st.warning(
                    "Debe ingresar el nombre del proveedor."
                )

            else:

                conexion = None
                cursor = None

                try:

                    conexion = obtener_conexion()
                    cursor = conexion.cursor()

                    cursor.execute("""
                        INSERT INTO Proveedor
                        (
                            Nombre_Completo,
                            Catalogo,
                            Telefono,
                            Correo
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        nombre.strip(),
                        catalogo.strip(),
                        telefono.strip(),
                        correo.strip()
                    ))

                    conexion.commit()

                    st.success(
                        "Proveedor registrado correctamente."
                    )

                except Exception as e:

                    if conexion:
                        conexion.rollback()

                    st.error(
                        f"Error al registrar proveedor: {e}"
                    )

                finally:

                    if cursor:
                        cursor.close()

                    if conexion:
                        conexion.close()

    # ==========================================
    # CONSULTAR PROVEEDORES
    # ==========================================

    with tab2:

        st.subheader("Proveedores registrados")

        conexion = None
        cursor = None

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    ID_Proveedor,
                    Nombre_Completo,
                    Catalogo,
                    Telefono,
                    Correo
                FROM Proveedor
                ORDER BY Nombre_Completo
            """)

            proveedores = cursor.fetchall()

            if proveedores:

                st.dataframe(
                    proveedores,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "No hay proveedores registrados."
                )

        except Exception as e:

            st.error(
                f"Error al consultar proveedores: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

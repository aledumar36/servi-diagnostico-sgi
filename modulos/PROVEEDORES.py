
import streamlit as st
import re
import json
from config.conexion import obtener_conexion


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def formatear_telefono(valor):
    digitos = re.sub(r"\D", "", valor)[:8]
    if len(digitos) > 4:
        return digitos[:4] + "-" + digitos[4:]
    return digitos


def validar_correo(correo):
    if not correo:
        return True

    return bool(re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        correo
    ))


def leer_catalogo(valor):
    if not valor:
        return []

    try:
        datos = json.loads(valor)
        if isinstance(datos, list):
            return [str(p) for p in datos]
    except (ValueError, TypeError):
        pass

    return [
        p.strip()
        for p in valor.splitlines()
        if p.strip()
    ]


def validar_proveedor(nombre, telefono, correo):
    if not nombre.strip():
        return "Ingrese el nombre del proveedor."

    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", nombre):
        return "El nombre debe contener letras."

    digitos = re.sub(r"\D", "", telefono)

    if telefono and len(digitos) != 8:
        return "El teléfono debe tener 8 dígitos."

    if not validar_correo(correo):
        return "Ingrese un correo válido."

    return None


# ==========================================
# MÓDULO PRINCIPAL
# ==========================================

def mostrar_proveedores():

    st.title("🚚 Compras y proveedores")
    st.write("Gestión de proveedores de Servi-Diagnóstico.")

    tab1, tab2, tab3 = st.tabs([
        "Registrar proveedor",
        "Consultar proveedores",
        "Editar / Eliminar"
    ])

    # ==========================================
    # REGISTRAR PROVEEDOR
    # ==========================================

    with tab1:

        st.subheader("Registrar nuevo proveedor")

        if "catalogo_nuevo" not in st.session_state:
            st.session_state.catalogo_nuevo = []

        nombre = st.text_input(
            "Nombre completo del proveedor *",
            key="nombre_proveedor"
        )

        telefono = st.text_input(
            "Teléfono",
            placeholder="Ej. 7123-4567",
            max_chars=9,
            key="telefono_proveedor"
        )

        correo = st.text_input(
            "Correo electrónico",
            placeholder="Ej. ventas@proveedor.com",
            key="correo_proveedor"
        )

        st.markdown("#### Catálogo de productos")

        producto = st.text_input(
            "Nombre del producto",
            placeholder="Ej. Tubos de extracción",
            key="producto_catalogo"
        )

        if st.button("➕ Agregar producto"):

            if producto.strip():
                if producto.strip() not in st.session_state.catalogo_nuevo:
                    st.session_state.catalogo_nuevo.append(
                        producto.strip()
                    )
                    st.rerun()
                else:
                    st.warning("Ese producto ya está agregado.")
            else:
                st.warning("Escriba el nombre del producto.")

        for i, item in enumerate(st.session_state.catalogo_nuevo):

            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(f"• {item}")

            with col2:
                if st.button("❌", key=f"quitar_nuevo_{i}"):
                    st.session_state.catalogo_nuevo.pop(i)
                    st.rerun()

        if st.button("💾 Guardar proveedor", type="primary"):

            error = validar_proveedor(
                nombre,
                telefono,
                correo
            )

            if error:
                st.warning(error)

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
                        json.dumps(
                            st.session_state.catalogo_nuevo,
                            ensure_ascii=False
                        ),
                        formatear_telefono(telefono),
                        correo.strip()
                    ))

                    conexion.commit()

                    st.session_state.catalogo_nuevo = []

                    st.success(
                        "Proveedor registrado correctamente."
                    )

                except Exception as e:
                    if conexion:
                        conexion.rollback()
                    st.error(f"Error al registrar proveedor: {e}")

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

                for p in proveedores:

                    with st.expander(
                        f"{p['ID_Proveedor']} - {p['Nombre_Completo']}"
                    ):
                        st.write(
                            f"**Teléfono:** {p['Telefono'] or 'No registrado'}"
                        )

                        st.write(
                            f"**Correo:** {p['Correo'] or 'No registrado'}"
                        )

                        st.write("**Catálogo:**")

                        catalogo = leer_catalogo(p["Catalogo"])

                        if catalogo:
                            for item in catalogo:
                                st.write(f"• {item}")
                        else:
                            st.info("Sin productos registrados.")

            else:
                st.info("No hay proveedores registrados.")

        except Exception as e:
            st.error(f"Error al consultar proveedores: {e}")

        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    # ==========================================
    # EDITAR Y ELIMINAR
    # ==========================================

    with tab3:

        st.subheader("Administrar proveedores")

        conexion = None
        cursor = None

        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM Proveedor
                ORDER BY Nombre_Completo
            """)

            proveedores = cursor.fetchall()

            if not proveedores:
                st.info("No hay proveedores registrados.")

            else:

                opciones = {
                    f"{p['ID_Proveedor']} - {p['Nombre_Completo']}": p
                    for p in proveedores
                }

                elegido = st.selectbox(
                    "Seleccione un proveedor",
                    list(opciones.keys())
                )

                proveedor = opciones[elegido]
                id_proveedor = proveedor["ID_Proveedor"]

                nombre_editado = st.text_input(
                    "Nombre del proveedor",
                    value=proveedor["Nombre_Completo"],
                    key=f"editar_nombre_{id_proveedor}"
                )

                telefono_editado = st.text_input(
                    "Teléfono",
                    value=proveedor["Telefono"] or "",
                    max_chars=9,
                    key=f"editar_telefono_{id_proveedor}"
                )

                correo_editado = st.text_input(
                    "Correo electrónico",
                    value=proveedor["Correo"] or "",
                    key=f"editar_correo_{id_proveedor}"
                )

                st.markdown("#### Editar catálogo")

                clave = f"catalogo_editar_{id_proveedor}"

                if clave not in st.session_state:
                    st.session_state[clave] = leer_catalogo(
                        proveedor["Catalogo"]
                    )

                nuevo_producto = st.text_input(
                    "Agregar producto al catálogo",
                    key=f"nuevo_producto_{id_proveedor}"
                )

                if st.button(
                    "➕ Agregar",
                    key=f"agregar_editar_{id_proveedor}"
                ):
                    if nuevo_producto.strip():
                        if nuevo_producto.strip() not in st.session_state[clave]:
                            st.session_state[clave].append(
                                nuevo_producto.strip()
                            )
                            st.rerun()
                        else:
                            st.warning("Ese producto ya está agregado.")

                for i, item in enumerate(st.session_state[clave]):

                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.write(f"• {item}")

                    with col2:
                        if st.button(
                            "❌",
                            key=f"eliminar_item_{id_proveedor}_{i}"
                        ):
                            st.session_state[clave].pop(i)
                            st.rerun()

                if st.button(
                    "💾 Guardar cambios",
                    key=f"guardar_{id_proveedor}",
                    type="primary"
                ):

                    error = validar_proveedor(
                        nombre_editado,
                        telefono_editado,
                        correo_editado
                    )

                    if error:
                        st.warning(error)

                    else:
                        cursor.execute("""
                            UPDATE Proveedor
                            SET
                                Nombre_Completo = %s,
                                Catalogo = %s,
                                Telefono = %s,
                                Correo = %s
                            WHERE ID_Proveedor = %s
                        """, (
                            nombre_editado.strip(),
                            json.dumps(
                                st.session_state[clave],
                                ensure_ascii=False
                            ),
                            formatear_telefono(telefono_editado),
                            correo_editado.strip(),
                            id_proveedor
                        ))

                        conexion.commit()

                        st.success(
                            "Proveedor actualizado correctamente."
                        )
                        st.rerun()

                st.divider()
                st.markdown("#### Eliminar proveedor")

                st.warning(
                    "No se puede eliminar un proveedor que "
                    "tenga productos u órdenes de compra asociados."
                )

                confirmar = st.checkbox(
                    "Confirmo que deseo eliminar este proveedor",
                    key=f"confirmar_{id_proveedor}"
                )

                if st.button(
                    "🗑️ Eliminar proveedor",
                    disabled=not confirmar,
                    key=f"eliminar_proveedor_{id_proveedor}"
                ):

                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM Producto
                        WHERE ID_Proveedor = %s
                    """, (id_proveedor,))

                    asociados = cursor.fetchone()["COUNT(*)"]

                    if asociados > 0:
                        st.error(
                            "No se puede eliminar este proveedor "
                            "porque tiene productos asociados."
                        )

                    else:
                        try:
                            cursor.execute("""
                                DELETE FROM Proveedor
                                WHERE ID_Proveedor = %s
                            """, (id_proveedor,))

                            conexion.commit()

                            st.success(
                                "Proveedor eliminado correctamente."
                            )

                            st.rerun()

                        except Exception:
                            conexion.rollback()
                            st.error(
                                "No se puede eliminar el proveedor "
                                "porque tiene registros relacionados."
                            )

        except Exception as e:
            if conexion:
                conexion.rollback()
            st.error(f"Error al administrar proveedores: {e}")

        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

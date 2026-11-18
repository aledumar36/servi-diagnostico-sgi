
import streamlit as st
from datetime import date
import phonenumbers
from phonenumbers import NumberParseException
from config.conexion import obtener_conexion


# Países disponibles para el registro
PAISES = {
    "El Salvador": "SV",
    "Guatemala": "GT",
    "Honduras": "HN",
    "Nicaragua": "NI",
    "Costa Rica": "CR",
    "Panamá": "PA",
    "Belice": "BZ",
    "México": "MX",
    "Estados Unidos": "US",
    "Canadá": "CA",
    "Colombia": "CO",
    "Venezuela": "VE",
    "Ecuador": "EC",
    "Perú": "PE",
    "Argentina": "AR",
    "Chile": "CL",
    "Brasil": "BR",
    "España": "ES",
    "Alemania": "DE",
    "Francia": "FR",
    "Italia": "IT",
    "Reino Unido": "GB"
}


def etiqueta_pais(nombre):
    region = PAISES[nombre]
    codigo = phonenumbers.country_code_for_region(region)
    return f"{nombre} (+{codigo})"


def validar_telefono(numero, region):
    """
    Valida un teléfono según el país seleccionado.
    Devuelve el número internacional o un mensaje de error.
    """

    numero = numero.strip()

    if not numero:
        return None, "Ingresá un número telefónico."

    # Solo se permiten dígitos y separadores habituales.
    caracteres_permitidos = set("0123456789 +-()")

    if any(c not in caracteres_permitidos for c in numero):
        return None, "El teléfono no debe contener letras ni símbolos inválidos."

    if numero.count("+") > 1 or ("+" in numero and not numero.startswith("+")):
        return None, "El signo + solamente puede aparecer al inicio."

    try:
        telefono = phonenumbers.parse(numero, region)

        codigo_esperado = phonenumbers.country_code_for_region(region)

        if telefono.country_code != codigo_esperado:
            return None, "El código internacional no coincide con el país seleccionado."

        if not phonenumbers.is_valid_number_for_region(telefono, region):
            return None, "El número no es válido para el país seleccionado."

        numero_internacional = phonenumbers.format_number(
            telefono,
            phonenumbers.PhoneNumberFormat.E164
        )

        return numero_internacional, None

    except NumberParseException:
        return None, "No se pudo interpretar el número telefónico."


def mostrar_pacientes():

    st.title("👥 Gestión de pacientes")
    st.write("Registro y consulta de pacientes de Servi-Diagnóstico.")

    pestaña_registro, pestaña_consulta = st.tabs(
        ["Registrar paciente", "Consultar pacientes"]
    )

    with pestaña_registro:

        st.subheader("Registrar nuevo paciente")

        with st.form("formulario_paciente"):

            nombre = st.text_input("Nombre completo *")

            st.markdown("#### Teléfono del paciente")

            pais = st.selectbox(
                "País del teléfono *",
                list(PAISES.keys()),
                format_func=etiqueta_pais
            )

            telefono = st.text_input(
                "Número telefónico *",
                placeholder="Ejemplo: 71234567",
                help="Ingresá el número nacional sin el código del país."
            )

            fecha_nacimiento = st.date_input(
                "Fecha de nacimiento",
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                value=date(2000, 1, 1),
                format="DD/MM/YYYY"
            )

            genero = st.selectbox(
                "Género",
                ["No especificado", "Masculino", "Femenino"]
            )

            dui = st.text_input("DUI (opcional)")
            correo = st.text_input("Correo electrónico")
            direccion = st.text_area("Dirección")

            st.markdown("#### Contacto de emergencia")

            pais_emergencia = st.selectbox(
                "País del teléfono de emergencia",
                list(PAISES.keys()),
                format_func=etiqueta_pais
            )

            telefono_emergencia = st.text_input(
                "Teléfono de emergencia (opcional)",
                placeholder="Ejemplo: 71234567"
            )

            guardar = st.form_submit_button(
                "Guardar paciente",
                use_container_width=True
            )

        if guardar:

            if not nombre.strip() or not telefono.strip():

                st.warning(
                    "El nombre y el teléfono son obligatorios."
                )

            else:

                telefono_validado, error_telefono = validar_telefono(
                    telefono,
                    PAISES[pais]
                )

                emergencia_validada = None
                error_emergencia = None

                if telefono_emergencia.strip():

                    emergencia_validada, error_emergencia = validar_telefono(
                        telefono_emergencia,
                        PAISES[pais_emergencia]
                    )

                if error_telefono:
                    st.error(
                        f"Teléfono del paciente: {error_telefono}"
                    )

                if error_emergencia:
                    st.error(
                        f"Teléfono de emergencia: {error_emergencia}"
                    )

                if not error_telefono and not error_emergencia:

                    conexion = None
                    cursor = None

                    try:

                        conexion = obtener_conexion()
                        cursor = conexion.cursor()

                        consulta = """
                            INSERT INTO Paciente (
                                Nombre_Completo,
                                Telefono,
                                Fecha_Nacimiento,
                                Genero,
                                DUI,
                                Correo,
                                Direccion,
                                Telefono_Emergencia
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """

                        valores = (
                            nombre.strip(),
                            telefono_validado,
                            fecha_nacimiento,
                            genero,
                            dui.strip() or None,
                            correo.strip() or None,
                            direccion.strip() or None,
                            emergencia_validada
                        )

                        cursor.execute(consulta, valores)
                        conexion.commit()

                        st.success(
                            "¡Paciente registrado correctamente!"
                        )

                        st.info(
                            f"Teléfono registrado: {telefono_validado}"
                        )

                    except Exception as error:

                        if conexion:
                            conexion.rollback()

                        st.error(
                            "No se pudo registrar el paciente. "
                            "Verificá los datos y que el DUI no esté registrado anteriormente."
                        )

                        st.error(str(error))

                    finally:

                        if cursor:
                            cursor.close()

                        if conexion:
                            conexion.close()

    with pestaña_consulta:

        st.subheader("Pacientes registrados")

        conexion = None
        cursor = None

        try:

            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    ID_Paciente,
                    Nombre_Completo,
                    Telefono,
                    Fecha_Nacimiento,
                    Genero,
                    DUI,
                    Correo
                FROM Paciente
                ORDER BY ID_Paciente DESC
            """)

            pacientes = cursor.fetchall()

            if pacientes:

                st.dataframe(
                    pacientes,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Todavía no hay pacientes registrados."
                )

        except Exception as error:

            st.error("No se pudieron consultar los pacientes.")
            st.error(str(error))

        finally:

            if cursor:
                cursor.close()

            if conexion:
                conexion.close()

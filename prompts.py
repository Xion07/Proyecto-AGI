# Textos que pronuncia el AGI de Google.
# Sin comas: el comando EXEC separa argumentos con comas y una coma
# dentro de la frase partiría el texto en dos.

POLITICA = (
    "La contraseña debe tener entre 6 y 8 dígitos. "
    "No puede tener todos los dígitos iguales. "
    "No puede ser una secuencia ni ser igual a su usuario."
)

PROMPTS = {
    "bienvenida": "Bienvenido al sistema de autenticación. Para ingresar como usuario marque 1. Para ingresar como administrador marque 2. Marque después del tono.",
    "opcion_invalida": "Opción no válida.",
    "pedir_usuario": "Digite su número de usuario seguido de la tecla numeral.",
    "pedir_clave": "Digite su contraseña seguida de la tecla numeral.",
    "login_ok": "Autenticación exitosa.",
    "login_fail": "Usuario o contraseña incorrectos.",
    "sin_permiso": "Esta cuenta no tiene permisos para ingresar por esta opción.",
    "intentos_agotados": "Superó el número de intentos permitidos.",

    "menu_usuario": "Para cambiar su contraseña marque 1. Para salir marque 9.",
    "menu_admin": "Para crear una cuenta de usuario marque 1. Para cambiar su contraseña marque 2. Para salir marque 9.",

    "pedir_clave_actual": "Digite su contraseña actual seguida de la tecla numeral.",
    "clave_actual_incorrecta": "La contraseña actual es incorrecta.",
    "pedir_clave_nueva": "Digite su nueva contraseña seguida de la tecla numeral.",
    "confirmar_clave_nueva": "Digite nuevamente la nueva contraseña para confirmar.",
    "claves_no_coinciden": "Las contraseñas no coinciden. No se realizó ningún cambio.",
    "clave_cambiada": "Su contraseña fue cambiada exitosamente.",

    "clave_longitud": "La contraseña debe tener entre 6 y 8 dígitos.",
    "clave_iguales": "La contraseña no puede tener todos los dígitos iguales.",
    "clave_secuencia": "La contraseña no puede ser una secuencia de números.",
    "clave_igual_usuario": "La contraseña no puede ser igual al usuario.",
    "clave_igual_actual": "La nueva contraseña no puede ser igual a la actual.",
    "politica_clave": POLITICA,

    "pedir_nuevo_usuario": "Digite el número del nuevo usuario seguido de la tecla numeral.",
    "usuario_invalido": "El número de usuario debe tener entre 3 y 8 dígitos.",
    "usuario_existe": "Ese usuario ya existe.",
    "pedir_clave_inicial": "Digite la contraseña inicial para el nuevo usuario seguida de la tecla numeral.",
    "va_a_crear": "Va a crear el usuario número",
    "confirmar_cancelar": "Para confirmar marque 1. Para cancelar marque 2.",
    "accion_cancelada": "Acción cancelada.",
    "cuenta_creada": "La cuenta fue creada exitosamente.",

    "despedida": "Gracias por usar el sistema. Hasta luego.",
    "error_sistema": "Ocurrió un error en el sistema. Intente más tarde.",
}

NOMBRES_DIGITO = [
    "cero", "uno", "dos", "tres", "cuatro",
    "cinco", "seis", "siete", "ocho", "nueve",
]

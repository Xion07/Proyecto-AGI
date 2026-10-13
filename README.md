# Proyecto AGI: Sistema de autenticación telefónica con Asterisk

Sistema de autenticación por llamadas telefónicas desarrollado con **Asterisk, PJSIP, Python AGI y SQLite**. El usuario interactúa con el sistema mediante tonos DTMF desde un softphone compatible con SIP.

Al llamar a la extensión **700**, se presenta un menú que permite ingresar como usuario o administrador.

## Funcionalidades

- Autenticación telefónica de usuarios y administradores.

- Validación de usuario y contraseña.

- Cambio de contraseña por parte del usuario autenticado.

- Creación de cuentas desde el menú de administración.

- Confirmación o cancelación de acciones importantes.

- Validación de contraseñas mediante una política definida.

- Mensajes de voz para orientar al usuario durante el proceso.

- Persistencia de las cuentas en una base de datos SQLite.

- Registro de actividad y opciones de diagnóstico desde la consola de Asterisk.

## Tecnologías

- **Asterisk:** central telefónica y ejecución del flujo de llamadas.

- **PJSIP:** registro y comunicación de extensiones SIP.

- **Python AGI:** lógica de autenticación y gestión de cuentas.

- **SQLite:** almacenamiento local de usuarios.

- **eSpeak NG y SoX:** generación y conversión de mensajes de audio.

- **Zoiper:** softphone utilizado para las pruebas.

- **Fedora 44:** sistema operativo de referencia para la instalación.

## Requisitos

Antes de instalar, asegúrate de contar con:

- Fedora 44 actualizado.

- Una cuenta con permisos `sudo`.

- Asterisk instalado y funcionando.

- Los archivos de este repositorio descargados en el equipo.

- Un softphone compatible con SIP, como Zoiper.

- Conectividad de red entre el softphone y el servidor Asterisk.

El instalador comprueba algunas dependencias del proyecto e intenta instalar `python3`, `espeak-ng` y `sox` cuando no están disponibles.

## Estructura del proyecto

Los archivos principales son:

| Archivo | Descripción |
|---|---|
| `auth.py` | Lógica de autenticación y menús interactivos del AGI. |
| `prompts.py` | Funciones relacionadas con los mensajes de voz. |
| `init_db.py` | Inicialización de la base de datos y las cuentas iniciales. |
| `generar_prompts.py` | Generación de los archivos de audio. |
| `extensions_agi.conf` | Dialplan para dirigir las llamadas a la aplicación AGI. |
| `pjsip_prueba.conf` | Configuración de una extensión SIP para pruebas. |
| `instalar.sh` | Instalación y configuración de los componentes del proyecto. |
| `Documentacion_Proyecto_AGI.docx` | Documentación ampliada del proyecto. |

## Instalación

### 1. Instalar y activar Asterisk

Si todavía no está instalado, ejecuta:

```bash

sudo dnf install -y asterisk asterisk-pjsip

```

Activa el servicio y verifica que esté funcionando:

```bash

sudo systemctl enable --now asterisk

sudo systemctl status asterisk

sudo asterisk -rx "core show version"

```

### 2. Descargar el proyecto

Clona el repositorio y entra en su carpeta. Reemplaza `USUARIO/REPOSITORIO` por la dirección real de tu repositorio de GitHub.

```bash

git clone https://github.com/Xion07/Proyecto-AGI.git

cd Proyecto-AGI

```

Si descargaste el proyecto como ZIP, descomprímelo y entra en la carpeta que contiene `instalar.sh`.

### 3. Ejecutar el instalador

Desde la carpeta del proyecto:

```bash

chmod +x instalar.sh

sudo bash instalar.sh

```

El instalador está diseñado para comprobar Asterisk, detectar rutas de instalación, preparar dependencias, copiar los archivos AGI, generar los audios, inicializar SQLite e instalar el dialplan.

Revisa los mensajes de la terminal y confirma que el proceso termine sin errores.

### 4. Verificar la extensión de la aplicación

Comprueba que Asterisk reconozca el contexto y la extensión:

```bash

sudo asterisk -rx "dialplan show agi-auth"

```

La salida debe mostrar la extensión `700`.

## Configuración de la extensión SIP de prueba

Si no tienes una extensión SIP configurada, el archivo `pjsip_prueba.conf` proporciona la configuración de referencia para el endpoint `6001`.

Copia el archivo a la configuración de Asterisk:

```bash

sudo cp pjsip_prueba.conf /etc/asterisk/pjsip_prueba.conf

```

Abre el archivo principal de PJSIP:

```bash

sudo nano /etc/asterisk/pjsip.conf

```

Agrega al final:

```text

#include "pjsip_prueba.conf"

```

Guarda los cambios y recarga PJSIP:

```bash

sudo asterisk -rx "pjsip reload"

sudo asterisk -rx "pjsip show endpoints"

sudo asterisk -rx "pjsip show endpoint 6001"

```

La extensión `6001` debe aparecer en la lista de endpoints. Si ya cuentas con una configuración PJSIP, verifica que la extensión utilizada tenga acceso al contexto `agi-auth`; no agregues configuraciones duplicadas.

## Configurar Zoiper

Crea una cuenta SIP en Zoiper con los datos correspondientes a la configuración de prueba:

| Campo | Valor |
|---|---|
| Usuario | `6001` |
| Contraseña SIP | `Prueba6001` |
| Servidor / Host | Dirección IP del servidor Asterisk |
| Puerto SIP | `5060` |
| Transporte | UDP |

La contraseña SIP es independiente de las credenciales de usuario y administrador de la aplicación.

Para consultar la dirección IP del equipo:

```bash

ip addr

```

Después de registrar la cuenta, verifica el contacto desde Asterisk:

```bash

sudo asterisk -rx "pjsip show contacts"

```

## Uso

Cuando la cuenta SIP esté registrada, marca **700** desde Zoiper.

El menú inicial ofrece estas opciones:

- `1`: ingresar como usuario.

- `2`: ingresar como administrador.

Durante la llamada, sigue las instrucciones de voz e introduce los dígitos solicitados. El símbolo `#` se utiliza para terminar la entrada cuando lo indique el flujo de la aplicación.

### Cuentas iniciales de prueba

La instalación crea estas credenciales iniciales:

| Rol | Usuario | Contraseña inicial |
|---|---|---|
| Administrador | `9999` | `482913` |
| Usuario | `1001` | `135792` |

**Importante:** son credenciales de demostración. Cámbialas después de las pruebas y no las reutilices en un entorno expuesto o de producción.

### Política de contraseñas

La política implementada establece que la contraseña:

- Debe tener entre 6 y 8 dígitos.

- No puede estar formada por un único dígito repetido.

- No puede ser una secuencia numérica.

- No puede ser igual al nombre de usuario.

- Al cambiarla, no puede ser igual a la contraseña actual.

## Pruebas funcionales recomendadas

Realiza las siguientes pruebas desde una llamada a la extensión `700`:

| Prueba | Acción | Resultado esperado |
|---|---|---|
| Inicio de sesión de usuario | Seleccionar `1` e ingresar las credenciales de usuario. | Acceso al menú de usuario. |
| Credenciales incorrectas | Introducir una contraseña equivocada. | El sistema rechaza el acceso. |
| Opción inválida | Introducir una opción que no esté en el menú. | Se informa que la opción no es válida. |
| Cambio de contraseña | Autenticarse y seguir el menú para cambiarla. | Se confirma el cambio si la nueva contraseña cumple la política. |
| Validación de contraseña | Probar una contraseña corta, repetida o secuencial. | Se rechaza la contraseña no válida. |
| Inicio de sesión administrativo | Seleccionar `2` e ingresar las credenciales administrativas. | Acceso al menú de administración. |
| Crear cuenta | Registrar un usuario nuevo y confirmar la acción. | La cuenta queda creada. |
| Cancelar creación | Cancelar antes de confirmar. | La cuenta no se crea. |
| Usuario duplicado | Intentar crear una cuenta existente. | Se informa que el usuario ya existe. |
| Verificar cuenta nueva | Cerrar la llamada e iniciar sesión con la cuenta creada. | La cuenta nueva puede autenticarse. |
| Salir | Seleccionar `9` en el menú correspondiente. | Se presenta el mensaje de despedida y finaliza la llamada. |

## Base de datos y registros

La base de datos SQLite normalmente se encuentra en:

```text

/var/lib/asterisk/agi_auth/usuarios.db

```

Para comprobar que exista:

```bash

sudo ls -l /var/lib/asterisk/agi_auth/

```

El registro de la aplicación puede consultarse con:

```bash

sudo cat /var/log/asterisk/agi_auth.log

```

Para observar las nuevas entradas en tiempo real:

```bash

sudo tail -f /var/log/asterisk/agi_auth.log

```

## Diagnóstico

### Asterisk no está activo

```bash

sudo systemctl restart asterisk

sudo systemctl status asterisk

```

### La extensión 700 no aparece

```bash

sudo asterisk -rx "dialplan reload"

sudo asterisk -rx "dialplan show agi-auth"

```

### Zoiper no se registra

Comprueba la IP del servidor, el usuario, la contraseña SIP y el puerto configurado. Después ejecuta:

```bash

sudo asterisk -rx "pjsip show endpoints"

sudo asterisk -rx "pjsip show contacts"

```

### No aparece el endpoint 6001

Verifica que `/etc/asterisk/pjsip.conf` incluya `pjsip_prueba.conf` y recarga PJSIP:

```bash

sudo asterisk -rx "pjsip reload"

```

### No se reproducen los audios

Comprueba que los archivos de audio existan:

```bash

sudo ls -l /var/lib/asterisk/sounds/agi_auth/

```

Si faltan archivos o la instalación quedó incompleta, revisa los mensajes del instalador y vuelve a ejecutarlo si corresponde:

```bash

sudo bash instalar.sh

```

### Revisar la ejecución del AGI

Abre la consola de Asterisk:

```bash

sudo asterisk -rvvv

```

Dentro de la consola, activa la depuración:

```text

agi set debug on

```

Realiza una llamada a `700` y revisa los mensajes. Para salir de la consola escribe `exit`.

### Permisos y SELinux

Si aparecen errores de acceso, revisa los permisos de los archivos AGI y de la base de datos. Fedora utiliza SELinux, por lo que también conviene consultar los registros del sistema antes de cambiar sus políticas de seguridad.

## Seguridad

- Cambia las credenciales iniciales antes de usar el sistema fuera de un entorno de pruebas.

- No publiques contraseñas reales, copias de bases de datos con usuarios reales ni registros que contengan información sensible.

- Limita el acceso SIP y de red a los equipos que necesiten utilizar el servicio.

- No expongas Asterisk directamente a Internet sin una configuración de seguridad adecuada.

- La configuración descrita es una guía de instalación y pruebas; no constituye por sí sola una auditoría de seguridad ni una garantía de preparación para producción.

## Integrantes del equipo

Proyecto desarrollado por los siguientes estudiantes:

- **Alejandro Lopez Ospina**
- **David Julian Pegagos Arroyave**
- **Mateo Blandon Mesa**
- **Ronald Jovanny Rodas Goez**

## Resultado esperado

Al completar la configuración, el sistema debe permitir llamar a la extensión `700`, autenticarse como usuario o administrador, validar credenciales, cambiar contraseñas, crear cuentas y confirmar o cancelar acciones. La base de datos conserva las cuentas para posteriores autenticaciones.

Para conocer con más detalle la implementación, consulta `https://docs.google.com/document/d/1X99H3EJ7HT2upTM_pF7mmlhaia_VbOEeNM0-x0r5m_M/edit?usp=sharing`.

---

**Proyecto académico:** autenticación telefónica con Asterisk AGI, Python y SQLite.


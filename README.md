# Proyecto AGI – Autenticación por voz con Asterisk

Este proyecto implementa un sistema de autenticación por teléfono usando **Asterisk, PJSIP, Python (AGI) y SQLite**.

Al llamar a la extensión **700**, el sistema presenta un menú inicial:

- **1:** ingreso como usuario
- **2:** ingreso como administrador

El usuario puede autenticarse y cambiar su contraseña. El administrador puede crear cuentas de usuario. Las contraseñas tienen una política definida y las acciones importantes solicitan confirmación o muestran un mensaje de resultado.

---

# 1. Requisitos

Este proyecto fue probado en **Fedora 44**.

Antes de comenzar se necesita:

- Fedora 44 actualizado.
- Asterisk instalado y funcionando.
- Una cuenta con permisos `sudo`.
- Conexión a Internet para instalar paquetes.
- Un softphone SIP. En las pruebas se utilizó **Zoiper**.
- Los archivos completos de este proyecto en una carpeta.

Los paquetes principales que utiliza el proyecto son:

- `asterisk`
- `asterisk-pjsip`
- `python3`
- `espeak-ng`
- `sox`

El instalador también revisa las dependencias `python3`, `espeak-ng` y `sox` y, si faltan, intenta instalarlas automáticamente.

---

# 2. Instalar Asterisk en Fedora 44

Si Asterisk todavía no está instalado:

```bash
sudo dnf install -y asterisk asterisk-pjsip
```

Activar el servicio para que inicie automáticamente:

```bash
sudo systemctl enable --now asterisk
```

Comprobar que está funcionando:

```bash
sudo systemctl status asterisk
```

También se puede comprobar directamente:

```bash
sudo asterisk -rx "core show version"
```

Debe aparecer la versión de Asterisk instalada.

Si el servicio no está iniciado, arrancarlo con:

```bash
sudo systemctl start asterisk
```

---

# 3. Entrar a la carpeta del proyecto

Ubicarse en la carpeta donde se copiaron los archivos del proyecto.

Por ejemplo:

```bash
cd ~/Documentos/Voz\ IP/Proyecto\ AGI/proyecto_agi_voip
```

Comprobar que estén los archivos:

```bash
ls
```

Se deben encontrar, entre otros:

```text
auth.py
prompts.py
init_db.py
generar_prompts.py
extensions_agi.conf
pjsip_prueba.conf
instalar.sh
Documentacion_Proyecto_AGI.docx
README.md
```

Si la carpeta está en otra ubicación, usar esa ruta.

---

# 4. Dar permisos al instalador

Ejecutar:

```bash
chmod +x instalar.sh
```

Comprobar:

```bash
ls -l instalar.sh
```

Debe aparecer el permiso de ejecución.

---

# 5. Ejecutar el instalador

Con Asterisk ya iniciado, ejecutar:

```bash
sudo bash instalar.sh
```

El instalador hace automáticamente varias tareas:

1. Comprueba que se esté ejecutando como administrador.
2. Comprueba que Asterisk esté instalado y respondiendo.
3. Detecta las rutas de Asterisk.
4. Detecta el usuario que ejecuta Asterisk.
5. Instala `python3`, `espeak-ng` y `sox` si hacen falta.
6. Copia `auth.py` al directorio de AGI.
7. Copia `prompts.py`, `init_db.py` y `generar_prompts.py`.
8. Genera los audios utilizados por el sistema.
9. Crea la base de datos SQLite.
10. Crea las cuentas iniciales.
11. Instala el dialplan.
12. Recarga el dialplan.
13. Comprueba que exista la extensión 700.
14. Ejecuta una autoprueba del AGI.

Al terminar correctamente debe aparecer un mensaje indicando que la instalación terminó y mostrando las cuentas iniciales.

El script está preparado para detectar las rutas de Asterisk en lugar de asumir una única distribución o instalación.

---

# 6. Cuentas iniciales

Para las primeras pruebas se crean dos cuentas:

### Administrador

```text
Usuario: 9999
Contraseña: 482913
```

### Usuario

```text
Usuario: 1001
Contraseña: 135792
```

Estas cuentas son únicamente para las pruebas iniciales. Después de comprobar el sistema se recomienda cambiar las contraseñas.

---

# 7. Base de datos

La base de datos utilizada por el AGI es SQLite.

Normalmente queda en:

```text
/var/lib/asterisk/agi_auth/usuarios.db
```

El instalador crea la carpeta y la base de datos y asigna los permisos necesarios para que Asterisk pueda utilizarla.

Para comprobar que existe:

```bash
sudo ls -l /var/lib/asterisk/agi_auth/
```

No es necesario modificar la base de datos manualmente para realizar las pruebas normales.

---

# 8. Dialplan

El sistema utiliza el contexto:

```text
[agi-auth]
```

y la extensión:

```text
700
```

El flujo es:

```text
700
 ↓
Answer()
 ↓
Wait(1)
 ↓
AGI(auth.py)
 ↓
Hangup()
```

El archivo `extensions_agi.conf` contiene esta configuración y el instalador la incluye desde `extensions.conf`.

Para comprobar que Asterisk reconoce la extensión:

```bash
sudo asterisk -rx "dialplan show agi-auth"
```

Debe aparecer la extensión:

```text
700
```

---

# 9. Configurar PJSIP para hacer las pruebas

Si ya se tienen extensiones SIP configuradas por otro trabajo, se pueden utilizar siempre que puedan acceder al contexto `agi-auth`.

Si no se tiene una extensión SIP, se puede utilizar el archivo:

```text
pjsip_prueba.conf
```

Este archivo crea una extensión de prueba:

```text
6001
```

con el contexto:

```text
agi-auth
```

y permite enviar los dígitos DTMF al AGI mediante:

```text
dtmf_mode=rfc4733
```

## Copiar la configuración

Copiar el archivo:

```bash
sudo cp pjsip_prueba.conf /etc/asterisk/pjsip_prueba.conf
```

Abrir la configuración de PJSIP:

```bash
sudo nano /etc/asterisk/pjsip.conf
```

Al final del archivo agregar:

```text
#include "pjsip_prueba.conf"
```

Guardar y salir.

Recargar PJSIP:

```bash
sudo asterisk -rx "pjsip reload"
```

Comprobar el endpoint:

```bash
sudo asterisk -rx "pjsip show endpoints"
```

Debe aparecer:

```text
6001
```

También se puede revisar específicamente:

```bash
sudo asterisk -rx "pjsip show endpoint 6001"
```

---

# 10. Configurar Zoiper

Instalar un softphone compatible con SIP. Para las pruebas se utilizó Zoiper.

Crear una cuenta SIP con estos datos:

```text
Usuario: 6001
Contraseña: Prueba6001
Servidor / Host: IP_DEL_SERVIDOR
Puerto SIP: 5060
Transporte: UDP
```

Por ejemplo, si la IP del computador es:

```text
192.168.1.43
```

el servidor será:

```text
192.168.1.43
```

La contraseña `Prueba6001` corresponde únicamente a la cuenta SIP. No es la contraseña del usuario 1001 ni la del administrador 9999.

Cuando Zoiper esté correctamente registrado, comprobar desde Asterisk:

```bash
sudo asterisk -rx "pjsip show contacts"
```

Debe aparecer un contacto para `6001`.

También se puede comprobar:

```bash
sudo asterisk -rx "pjsip show endpoint 6001"
```

---

# 11. Primera prueba: llamar a la extensión 700

Desde Zoiper marcar:

```text
700
```

Debe escucharse un mensaje similar a:

```text
Bienvenido al sistema de autenticación.
Para ingresar como usuario marque 1.
Para ingresar como administrador marque 2.
```

A partir de este punto se pueden realizar las pruebas funcionales.

---

# 12. Prueba 1 – Ingreso como usuario

### Objetivo

Comprobar que un usuario pueda autenticarse utilizando su usuario y contraseña.

### Pasos

1. Marcar:

```text
700
```

2. Cuando aparezca el menú inicial, marcar:

```text
1
```

3. Digitar:

```text
1001#
```

4. Digitar la contraseña:

```text
135792#
```

### Resultado esperado

Debe escucharse:

```text
Autenticación exitosa.
```

Después debe aparecer el menú de usuario:

```text
Para cambiar su contraseña marque 1.
Para salir marque 9.
```

Esto comprueba:

- Selección de usuario.
- Solicitud de usuario.
- Solicitud de contraseña.
- Validación de credenciales.
- Acceso al menú de usuario.

---

# 13. Prueba 2 – Contraseña incorrecta

### Objetivo

Comprobar que el sistema rechace credenciales incorrectas.

1. Marcar:

```text
700
```

2. Seleccionar:

```text
1
```

3. Introducir:

```text
1001#
```

4. Introducir una contraseña incorrecta.

Por ejemplo:

```text
123456#
```

### Resultado esperado

Debe aparecer:

```text
Usuario o contraseña incorrectos.
```

El sistema debe permitir nuevamente la autenticación según el número de intentos configurado.

---

# 14. Prueba 3 – Opción inválida

### Objetivo

Comprobar el manejo de entradas no válidas.

Desde el menú inicial introducir un número que no corresponda a las opciones disponibles, por ejemplo:

```text
5
```

### Resultado esperado

Debe aparecer:

```text
Opción no válida.
```

El sistema debe volver a presentar el menú.

Esta misma prueba se puede realizar dentro del menú de usuario o administrador.

---

# 15. Prueba 4 – Cambio de contraseña del usuario

### Objetivo

Comprobar que el usuario pueda cambiar su contraseña.

1. Marcar:

```text
700
```

2. Seleccionar:

```text
1
```

3. Autenticarse:

```text
1001#
135792#
```

4. En el menú de usuario seleccionar:

```text
1
```

5. Introducir la contraseña actual:

```text
135792#
```

6. Introducir una contraseña nueva válida. Por ejemplo:

```text
135798#
```

7. Volver a introducir la nueva contraseña:

```text
135798#
```

### Resultado esperado

Debe aparecer:

```text
Su contraseña fue cambiada exitosamente.
```

Después se presenta nuevamente el menú de usuario.

---

# 16. Prueba 5 – Confirmar que el cambio de contraseña quedó guardado

Esta prueba es importante porque no solamente comprueba que aparezca el mensaje, sino que verifica que el cambio se haya guardado.

### Primera llamada

Intentar entrar con:

```text
1001
135792
```

### Resultado esperado

La contraseña anterior debe ser rechazada.

### Segunda llamada

Intentar entrar con:

```text
1001
135798
```

### Resultado esperado

Debe aparecer:

```text
Autenticación exitosa.
```

De esta forma se comprueba que la nueva contraseña quedó almacenada.

---

# 17. Prueba 6 – Ingreso como administrador

### Objetivo

Comprobar el acceso al menú administrativo.

1. Marcar:

```text
700
```

2. Seleccionar:

```text
2
```

3. Introducir:

```text
9999#
```

4. Introducir:

```text
482913#
```

### Resultado esperado

Debe aparecer:

```text
Autenticación exitosa.
```

y después el menú:

```text
Para crear una cuenta de usuario marque 1.
Para cambiar su contraseña marque 2.
Para salir marque 9.
```

---

# 18. Prueba 7 – Contraseña inválida por longitud

La política del proyecto establece:

- Entre 6 y 8 dígitos.
- No puede tener todos los dígitos iguales.
- No puede ser una secuencia.
- No puede ser igual al usuario.
- Al cambiar contraseña, no puede ser igual a la contraseña actual.

Por ejemplo, probar:

```text
12345
```

### Resultado esperado

Debe aparecer un mensaje indicando que la contraseña debe tener entre 6 y 8 dígitos.

---

# 19. Prueba 8 – Contraseña con todos los dígitos iguales

Probar:

```text
111111
```

### Resultado esperado

Debe aparecer:

```text
La contraseña no puede tener todos los dígitos iguales.
```

La cuenta no debe crearse ni debe realizarse el cambio mientras la contraseña incumpla la política.

---

# 20. Prueba 9 – Contraseña secuencial

Probar una contraseña como:

```text
123456
```

### Resultado esperado

Debe aparecer:

```text
La contraseña no puede ser una secuencia de números.
```

---

# 21. Prueba 10 – Contraseña igual al usuario

Si el usuario es:

```text
123456
```

no se debe permitir utilizar:

```text
123456
```

como contraseña.

### Resultado esperado

Debe aparecer:

```text
La contraseña no puede ser igual al usuario.
```

---

# 22. Prueba 11 – Crear una cuenta como administrador

### Objetivo

Comprobar que el administrador pueda crear una nueva cuenta.

1. Marcar:

```text
700
```

2. Seleccionar administrador:

```text
2
```

3. Ingresar:

```text
9999#
482913#
```

4. En el menú administrativo seleccionar:

```text
1
```

5. Introducir un usuario nuevo, por ejemplo:

```text
2001#
```

6. Introducir una contraseña válida, por ejemplo:

```text
258741#
```

7. El sistema debe presentar los datos de la cuenta que se va a crear.

8. Cuando solicite confirmación, marcar:

```text
1
```

### Resultado esperado

Debe aparecer:

```text
La cuenta fue creada exitosamente.
```

Después debe volver al menú administrativo.

---

# 23. Prueba 12 – Cancelar creación de cuenta

Repetir el proceso de creación de una cuenta.

Cuando aparezca:

```text
Para confirmar marque 1.
Para cancelar marque 2.
```

seleccionar:

```text
2
```

### Resultado esperado

Debe aparecer:

```text
Acción cancelada.
```

La cuenta no debe crearse.

---

# 24. Prueba 13 – Usuario existente

Desde el menú de administrador intentar crear nuevamente un usuario que ya exista, por ejemplo:

```text
1001#
```

### Resultado esperado

Debe aparecer:

```text
Ese usuario ya existe.
```

No debe sobrescribirse la cuenta existente.

---

# 25. Prueba 14 – Comprobar la cuenta creada

Después de crear correctamente, por ejemplo:

```text
2001
258741
```

cerrar la llamada.

Realizar una nueva llamada al:

```text
700
```

Seleccionar:

```text
1
```

e ingresar:

```text
2001#
258741#
```

### Resultado esperado

Debe aparecer:

```text
Autenticación exitosa.
```

Esto confirma que la cuenta creada por el administrador quedó almacenada y puede utilizarse.

---

# 26. Prueba 15 – Salir

Desde el menú de usuario o administrador seleccionar:

```text
9
```

### Resultado esperado

Debe aparecer:

```text
Gracias por usar el sistema. Hasta luego.
```

y la llamada debe finalizar.

---

# 27. Ver las pruebas directamente desde Asterisk

Para observar lo que sucede mientras se realiza una llamada:

```bash
sudo asterisk -rvvv
```

Dentro de la consola de Asterisk se puede activar el debug del AGI:

```text
agi set debug on
```

Después llamar al:

```text
700
```

Se podrán observar mensajes como:

```text
Launched AGI Script /usr/share/asterisk/agi-bin/auth.py
Playing 'agi_auth/bienvenida.slin'
Playing 'agi_auth/pedir_usuario.slin'
Playing 'agi_auth/pedir_clave.slin'
Playing 'agi_auth/login_ok.slin'
Playing 'agi_auth/menu_usuario.slin'
```

Para salir de la consola:

```text
exit
```

---

# 28. Revisar el registro del proyecto

También se puede revisar:

```bash
sudo cat /var/log/asterisk/agi_auth.log
```

Para seguir el archivo mientras se realiza una llamada:

```bash
sudo tail -f /var/log/asterisk/agi_auth.log
```

---

# 29. Verificar PJSIP

Si Zoiper no registra la cuenta:

```bash
sudo asterisk -rx "pjsip show contacts"
```

Si no aparece `6001`, revisar:

```bash
sudo asterisk -rx "pjsip show endpoint 6001"
```

También se puede recargar PJSIP:

```bash
sudo asterisk -rx "pjsip reload"
```

---

# 30. Problemas frecuentes en Fedora 44

## Asterisk no está iniciado

```bash
sudo systemctl start asterisk
```

y:

```bash
sudo systemctl status asterisk
```

## El instalador dice que Asterisk no responde

Comprobar:

```bash
sudo asterisk -rx "core show version"
```

Si no responde:

```bash
sudo systemctl restart asterisk
```

## No aparece la extensión 700

Ejecutar:

```bash
sudo asterisk -rx "dialplan reload"
```

y:

```bash
sudo asterisk -rx "dialplan show agi-auth"
```

## No aparece el endpoint 6001

Comprobar que exista:

```text
/etc/asterisk/pjsip_prueba.conf
```

y que `/etc/asterisk/pjsip.conf` tenga:

```text
#include "pjsip_prueba.conf"
```

Después:

```bash
sudo asterisk -rx "pjsip reload"
```

## Zoiper no registra

Comprobar la IP del computador:

```bash
ip addr
```

Usar la IP de la interfaz de red que esté conectada.

Después revisar:

```bash
sudo asterisk -rx "pjsip show contacts"
```

## El AGI no reproduce los audios

Comprobar que existan:

```bash
sudo ls -l /var/lib/asterisk/sounds/agi_auth/
```

Si faltan, ejecutar nuevamente:

```bash
sudo bash instalar.sh
```

## El AGI tiene problemas de permisos

Comprobar:

```bash
ls -l /var/lib/asterisk/agi_auth/
```

y:

```bash
ls -l /var/lib/asterisk/agi-bin/auth.py
```

El instalador intenta dejar los archivos con el usuario y grupo de Asterisk.

## Problemas relacionados con SELinux

En Fedora el instalador ejecuta `restorecon` sobre las rutas utilizadas por el proyecto. Si aun así se presenta un problema, revisar los mensajes del sistema y el log de Asterisk antes de cambiar políticas de SELinux.

---

# 31. Resumen de la prueba completa

Para presentar el proyecto se recomienda realizar las pruebas en este orden:

### Usuario

```text
700
→ 1
→ 1001
→ 135792
→ autenticación exitosa
```

### Opción inválida

```text
700
→ opción incorrecta
→ "Opción no válida"
```

### Cambio de contraseña

```text
700
→ 1
→ 1001
→ contraseña actual
→ 1
→ contraseña nueva
→ confirmar
→ "Su contraseña fue cambiada exitosamente"
```

### Comprobar cambio

```text
Contraseña anterior → rechazada
Contraseña nueva → aceptada
```

### Administrador

```text
700
→ 2
→ 9999
→ 482913
→ menú administrador
```

### Validación de contraseña

Probar:

```text
12345    → longitud
111111   → todos iguales
123456   → secuencia
```

### Crear usuario

```text
Administrador
→ crear cuenta
→ nuevo usuario
→ contraseña válida
→ confirmar con 1
→ "La cuenta fue creada exitosamente"
```

### Comprobar usuario creado

```text
700
→ 1
→ nuevo usuario
→ contraseña nueva
→ autenticación exitosa
```

### Cancelar una acción

```text
Crear cuenta
→ confirmar/cancelar
→ 2
→ "Acción cancelada"
```

### Salir

```text
9
→ "Gracias por usar el sistema. Hasta luego."
```

---

# 32. Resultado esperado del proyecto

Al finalizar las pruebas se debe poder demostrar que:

- El sistema inicia correctamente en Fedora 44.
- Asterisk reconoce la extensión 700.
- El softphone se registra mediante PJSIP.
- El AGI `auth.py` se ejecuta al llamar al 700.
- Se puede ingresar como usuario.
- Se puede ingresar como administrador.
- Las credenciales incorrectas son rechazadas.
- Las opciones inválidas son controladas.
- El usuario puede cambiar su contraseña.
- El cambio de contraseña queda almacenado.
- Las contraseñas se validan con la política definida.
- El administrador puede crear usuarios.
- Se puede confirmar o cancelar la creación.
- Un usuario creado puede autenticarse posteriormente.
- Las acciones muestran mensajes de resultado.
- La llamada puede finalizar correctamente.

La documentación más detallada del proyecto se encuentra en:

```text
Documentacion_Proyecto_AGI.docx
```

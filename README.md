# Proyecto AGI – Autenticación por voz (Asterisk)

Marcando la extensión **700** el sistema ofrece: 1 = usuario, 2 = administrador.
Las frases las pronuncia el AGI de Google que ya está en Issabel (`googletts.agi`).

## Instalación
Con Asterisk corriendo y los archivos de esta carpeta en el servidor:

```bash
sudo bash instalar.sh
```

El script detecta las rutas de Asterisk y el AGI de Google, copia los scripts,
crea la base de datos, instala el dialplan y recarga. Si ya habías instalado
una prueba en la extensión 701, este instalador la quita y deja solo la 700.

Si no encuentra el sintetizador:

```bash
sudo GOOGLE_AGI=/ruta/googletts.agi bash instalar.sh
```

## Probar
1. Llama al **702**. Si escuchas la frase, Google responde.
2. Llama al **700**.
3. Administrador: opción 2, `9999` / `482913`.
4. Usuario: opción 1, `1001` / `135792`.

Marca después del bip. En usuario y clave termina con la tecla numeral.
En los menús basta un dígito.

La primera vez que se dice cada frase puede tardar unos segundos. Después
queda en `/tmp`. La máquina necesita salida a `translate.google.com`.

## Si algo falla
`sudo asterisk -rvvv`, luego `agi set debug on`, y revisa `/var/log/asterisk/agi_auth.log`.
En la consola debe aparecer `Google TTS:` y el comando `EXEC AGI`.

`pjsip_prueba.conf` solo hace falta si todavía no tienes un softphone que llegue al 700.

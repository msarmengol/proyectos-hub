# ⚡ ProjectHub - Fichas de Proyectos

Aplicación web local y ligera desarrollada en **Python (FastAPI)** y **SQLite** para catalogar, documentar y gestionar todos tus proyectos e ideas de desarrollo en un solo lugar.

---

## 🎯 Características Principales

- **Ficha Integral por Proyecto**:
  - **Identificación:** Nombre, descripción resumida, estado (`💡 Idea`, `🚧 En desarrollo`, `🚀 Producción`, `⏸️ Pausado`, `📦 Archivado`), categoría y prioridad.
  - **📋 Alcance Funcional:** Objetivos, problemas que resuelve, funcionalidades del MVP y notas de negocio.
  - **⚙️ Detalles Técnicos:** Stack tecnológico, ruta local, repositorio Git, comando de ejecución rápido (con botón para copiar en 1 clic) y notas de arquitectura/puertos.
  - **🎯 Próximos Pasos (Roadmap):** Checklist interactivo de tareas pendientes actualizable directamente desde la ficha.
- **Ideas sin código:** Puedes registrar ideas en 10 segundos indicando solo el nombre y la idea, dejando todos los campos técnicos para más adelante.
- **🔍 Auto-Escaneo de Carpetas:** Botón para escanear directorios locales (ej. `/home/ubuntu`) y detectar automáticamente proyectos existentes (inspecciona `README`, `package.json`, `requirements.txt`, git remote, `docker-compose.yml`) para importarlos con 1 clic.
- **Buscador y Filtros en Tiempo Real:** Filtra al instante por estado, categoría o busca por cualquier palabra clave.
- **Exportación / Backup:**
  - Exportación de la ficha individual a formato **Markdown (`.md`)**.
  - Copia de seguridad completa en **JSON** con importación/restauración con 1 clic.
- **Persistencia en SQLite:** Base de datos local ultra rápida (`projects.db`) con modo WAL activo.

---

## 🚀 Cómo Arrancar la Aplicación

La aplicación ya cuenta con su entorno virtual configurado en `proyectos-hub/venv`.

### 1. Iniciar el servidor
```bash
cd /home/ubuntu/proyectos-hub
./run.sh
```

Por defecto se inicia en `http://localhost:8000` (accesible también en tu red local o IP pública en el puerto 8000).

Si quieres cambiar el puerto:
```bash
PORT=8080 ./run.sh
```

---

## 📂 Estructura del Proyecto

```
/home/ubuntu/proyectos-hub/
├── app/
│   ├── database.py       # Capa de datos SQLite y consultas
│   ├── scanner.py        # Detector automático de proyectos en disco
│   └── main.py           # API REST con FastAPI
├── templates/
│   └── index.html        # Interfaz web responsiva (Tailwind CSS + JS)
├── projects.db           # Base de datos SQLite local
├── requirements.txt      # Dependencias Python
└── run.sh                # Script de arranque rápido
```

---

## 🔄 Ejecutar como Servicio en Segundo Plano (Opcional con systemd)

Si deseas que se mantenga siempre encendida o inicie con el sistema:

1. Crea el archivo de servicio:
   ```bash
   sudo nano /etc/systemd/system/projecthub.service
   ```
2. Pega la configuración:
   ```ini
   [Unit]
   Description=ProjectHub - Fichas de Proyectos
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/proyectos-hub
   ExecStart=/home/ubuntu/proyectos-hub/run.sh
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
3. Actívalo:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now projecthub
   ```

# 🥗 Dont Wasted It

> **Sistema web para la reducción del desperdicio de alimentos en cafeterías, restaurantes y universidades.**

**"Dont Wasted It"** es una plataforma digital diseñada para conectar a establecimientos de alimentos (cafeterías, restaurantes y comedores universitarios) con estudiantes y consumidores interesados en adquirir, a precios reducidos, los alimentos próximos a vencer o que sobraron al final de la jornada.

---

## 🎯 Objetivo del Proyecto

Reducir el desperdicio de alimentos en el eslabón final de la cadena alimentaria, generando un modelo de triple impacto:
* **Para consumidores y estudiantes:** Acceso a alimentos en buen estado con descuentos significativos y gamificación mediante puntos e indicadores de impacto.
* **Para establecimientos:** Canal adicional de ingresos sobre productos excedentes que de otro modo terminarían en la basura.
* **Para el medio ambiente:** Disminución de residuos orgánicos y de la huella asociada al desperdicio alimentario.

---

## ✨ Funcionalidades Principales

### 👤 Módulo Cliente (Estudiantes / Consumidores)
* **Exploración por Zonas y Localidades:** Consulta de la oferta mediante listas desplegables organizadas por zonas/localidades para ubicar comercios cercanos.
* **Filtros de Búsqueda:** Filtrado rápido de ofertas por rango de precio y tipo de alimento.
* **Reserva y Pago:** Bloqueo inmediato del excedente al confirmar el pago y generación de un **código único de recogida**.
* **Gamificación y Contador de Impacto:** Acumulación de puntos por cada compra confirmada y seguimiento personal de **kilogramos de comida rescatada**.

### 🏪 Módulo Establecimiento (Dueños de Negocio)
* **Gestión de Local y Zona:** Registro del establecimiento y vinculación a una zona o localidad específica.
* **Publicación de Excedentes:** Creación de ofertas especificando descripción, cantidad disponible, precio reducido y hora límite de recogida.
* **Control de Entregas:** Validación y confirmación de pedidos mediante el código de recogida presentado por el cliente.
* **Panel de Reportes:** Visualización de reservas pendientes, historial de ventas (COP), porciones entregadas e impacto ambiental acumulado.

---

## 🏗️ Arquitectura del Sistema

La plataforma está estructurada en cuatro componentes principales:

1. **Aplicación Web (Frontend):** Interfaz responsiva adaptable a dispositivos móviles para la publicación (comercios) y exploración/compra (clientes).
2. **Backend / API:** Lógica de negocio centralizada, gestión de reservas concurrentes, cálculo de puntos y actualización del contador de impacto.
3. **Base de Datos:** Almacenamiento relacional de usuarios, comercios, publicaciones, reservas y transacciones.
4. **Catálogo de Zonas:** Módulo de organización geográfica por localidades y sus establecimientos asociados.

```text
[ Comercios ] ──(Publican excedentes)──┐
                                       ▼
                              [ Aplicación Web ] ◄──► [ Backend / API ] ◄──► [ Base de Datos ]
                                       ▲                      │
[ Usuarios ]  ──(Consultan/Compran)────┘                      ▼
                                                    [ Catálogo de Zonas ]

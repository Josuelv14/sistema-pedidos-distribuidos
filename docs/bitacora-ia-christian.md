# Bitácora de uso de IA — Christian

## Consultas y uso de las respuestas

| Quién consultó | Qué pregunté | Qué respondió la herramienta | Qué hice con la respuesta |
| --- | --- | --- | --- |
| Christian | ¿Cómo implemento las notificaciones WebSocket en la API del equipo? | Sugirió registrar las conexiones por ID de pedido, activar el aviso al guardar `READY` y consultar el estado actual al reconectarse. | Incorporé el servicio de notificaciones y la ruta `/ws/orders/{order_id}`. Registré los cambios en dos commits. |
| Christian | ¿Cómo pruebo el aviso y la desconexión con caja y cocina activas? | Propuso probar con dos pedidos. En el primero, mantener la conexión abierta al marcarlo listo. En el segundo, cerrarla antes de completar el pedido y volver a conectarse. | Ejecuté ambas pruebas desde Swagger y la consola del navegador. Observé `order_ready` en la primera y `order_status` con `READY` al reconectar en la segunda. Registré los resultados en [prueba-websockets.md](prueba-websockets.md). |
| Christian | ¿Cómo organizo el ADR de WebSockets y el comparativo? | Sugirió una estructura de contexto, decisión, alternativas y consecuencias. Ayudó a ordenar el comparativo usando los ADR existentes. | Usé esa estructura para preparar los borradores de los ADR 004 y 005. |

## Reflexión

La primera guía proponía usar `PATCH` para simular que el pedido quedaba listo. Al revisar la versión del equipo, vi que ya existía `POST /orders/{order_id}/ready`, que confirma el cambio con cocina por TCP. Usé esa ruta en las pruebas para comprobar que el aviso funcionaba dentro del flujo completo. También tuve que usar Python 3.12 porque la instalación de la versión de gRPC fijada por el proyecto falló en mi entorno con Python 3.13.
# Escenarios de atributos de calidad

El orden de prioridad considera primero la
integridad de pedidos y pagos, luego la disponibilidad y la notificación. Las
medidas son criterios esperados; no representan tiempos medidos en las pruebas.

| Orden | Atributo | Fuente y estímulo | Entorno y elemento afectado | Respuesta esperada y medida | Evidencia |
| --- | --- | --- | --- | --- | --- |
| 1 | Integridad e idempotencia | El estudiante repite la creación con igual clave y contenido. | REST activo; servicio de pedidos. | Devolver el mismo ID y conservar un solo pedido. Si cambia el contenido, responder `409`. | Procedimiento de idempotencia del README; pruebas de integración de caja y cocina para el mismo pedido. |
| 2 | Disponibilidad | Un estudiante solicita un pago cuando caja no responde. | REST activo, caja detenida; cliente gRPC. | Limitar la llamada a dos segundos, devolver `503`, conservar `PENDING` y permitir reintentar. | [Prueba gRPC](prueba-grpc.md), `tests/test_billing.py`. |
| 3 | Confiabilidad del pago | El cliente reintenta después de que caja aprobó el pago y cocina no respondió. | Caja activa, cocina detenida; despacho TCP. | Conservar `PAID`, devolver `503` y permitir despachar después sin un segundo cobro. | [Prueba TCP](prueba-tcp.md), prueba `test_09` de cocina. |
| 4 | Robustez | Un cliente TCP envía JSON incorrecto o se desconecta durante un mensaje. | Cocina activa; servidor TCP. | Rechazar el mensaje inválido y atender la siguiente solicitud válida sin reiniciar el servidor. Limitar a 4096 bytes por mensaje y dos segundos de espera. | [Prueba TCP](prueba-tcp.md), pruebas `test_04` y `test_05`. |
| 5 | Continuidad ante desconexión | El estudiante cierra WebSockets durante la preparación y vuelve después. | REST y cocina activos; suscripción al pedido. | Permitir completar cocina sin el cliente y devolver `order_status` con `READY` al reconectar al mismo ID. | [Prueba WebSockets, caso 2](prueba-websockets.md). |
| 6 | Notificación asíncrona | El operador marca listo un pedido con un estudiante conectado. | Servicios activos; evento local y WebSockets. | Enviar `order_ready` con el ID y `READY` mediante la conexión abierta, sin otra consulta del cliente. | [Prueba WebSockets, caso 1](prueba-websockets.md). |

Los servicios mantienen datos en memoria. Estos escenarios no garantizan
recuperación de datos después de reiniciar los procesos ni entrega persistente
de notificaciones.

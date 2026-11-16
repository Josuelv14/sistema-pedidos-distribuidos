# ADR-004: Notificaciones de pedidos mediante WebSockets

- **Estado:** Aceptado
- **Fecha:** [2026-11-16]
- **Decisores:** Equipo del sistema de pedidos

## Contexto

El estudiante necesita saber cuándo su pedido está listo. Cuando el personal
de cocina termina la preparación, el servicio de pedidos recibe la
confirmación por TCP y guarda el estado `READY`. El estudiante puede perder
la conexión mientras el pedido sigue en preparación.

## Decisión

El cliente se conecta a `/ws/orders/{order_id}` para seguir un pedido.
Al abrir la conexión, recibe `order_status` con el estado guardado.

Cuando cocina confirma la preparación mediante `POST /orders/{order_id}/ready`,
el servicio guarda `READY` y activa el aviso. Si el cliente sigue conectado,
recibe `order_ready` y el servidor cierra la conexión. Si el cliente se
desconectó antes, puede volver a abrir la conexión y recibir `order_status`
con `READY`.

Elegimos WebSockets porque queríamos que el estudiante se enterara apenas su pedido estuviera listo, sin tener que consultar su estado a cada rato. Mientras la conexión está abierta, el servidor puede enviar el aviso en cuanto guarda el estado `READY`. Si el estudiante pierde la conexión durante la preparación, puede volver a conectarse y ver el estado actualizado del pedido.

## Alternativas consideradas

1. **Consulta periódica por REST.** El cliente podría consultar
   `GET /orders/{order_id}` cada cierto tiempo. El aviso llegaría en la
   siguiente consulta y el cliente haría solicitudes aunque el estado no
   hubiera cambiado.

## Consecuencias

### Positivas

- El estudiante conectado recibe el aviso cuando el sistema guarda `READY`.
- Cocina puede terminar el pedido aunque el estudiante se desconecte.
- La reconexión permite recuperar el estado actual del pedido.

### Negativas y limitaciones

- Las conexiones y los pedidos se mantienen en memoria del proceso.
- Si se reinicia el servicio, se pierden los pedidos guardados en memoria.
- La reconexión recupera el estado actual. El sistema no conserva un
  historial de avisos para reenviarlos.

La verificación se describe en las
[pruebas de WebSockets](prueba-websockets.md).
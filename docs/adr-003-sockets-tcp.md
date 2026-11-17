# ADR-003 — Sockets TCP entre pedidos y cocina

**Estado:** Aceptado e implementado.
**Responsable:** Integrante 3 (cocina).
**Asistencia de IA:** Estructura y redacción elaboradas con asistencia de ChatGPT.

## Contexto

La API REST crea el pedido y caja procesa el pago por gRPC. La cocina debe recibir
las órdenes pagadas, procesarlas y confirmar su estado. Este mecanismo es el
tercero de los cuatro definidos por el grupo y debe funcionar dentro del flujo
REST → gRPC → Sockets TCP → notificación WebSockets.

## Decisión implementada

Se usa un servidor Python con `socketserver.ThreadingTCPServer` en
`127.0.0.1:50052`. El servicio de pedidos utiliza un cliente `socket` para
abrir conexiones TCP bajo demanda. Cada operación intercambia exactamente un
mensaje JSON terminado en salto de línea y una respuesta JSON terminada igual.
Se emplea petición/respuesta **síncrona** con tiempo máximo de espera de 2 s;
la notificación asíncrona corresponderá al servicio WebSockets del integrante 4.

Operaciones del protocolo: `CREATE_ORDER`, `GET_ORDER` y `READY_ORDER`.
La cocina conserva `PREPARING` / `READY` en memoria y evita registrar dos veces
el mismo ID. Un ID repetido con diferente producto o cantidad se rechaza.

## Alternativas consideradas

- REST interno: sencillo, pero no demostraría un mecanismo adicional diferente.
- gRPC interno: validación de mensajes estructurada, pero se utilizará en caja.
- Kafka: apropiado para colas de eventos y desacoplamiento; requiere
  infraestructura adicional no prevista en este alcance.
- Sockets TCP: permite demostrar encuadre de mensajes, control explícito de
  conexión y tolerancia a fallos, a costa de construir el protocolo.

## Consecuencias

**Ventajas:** conexión entre procesos independientes, protocolo pequeño,
idempotencia por ID, límites de espera y errores controlados.

**Limitaciones:** datos perdidos al reiniciar cocina; sin persistencia ni cola de
reintentos automáticos; TCP garantiza orden de bytes en una conexión, pero no
entrega de mensajes de negocio exactamente una vez. El estado `READY` se activa
mediante una acción REST del operador que comunica a cocina por TCP, en lugar
de simular una preparación automática. El endpoint REST existente de cambio
manual de estado sigue disponible y podría omitir la comunicación TCP;
coordinar con el equipo si se restringe para la entrega.

## Escenarios de calidad vinculados

1. **Disponibilidad:** dado un servicio TCP caído, cuando la API intenta enviar
   un pedido pagado, debe responder `503` sin perder el estado `PAID` y permitir
   un reintento posterior.
2. **Confiabilidad:** dado un pedido ya registrado en cocina, cuando se repite
   `CREATE_ORDER` con el mismo ID y contenido, debe conservar una sola entrada
   y responder `duplicate: true`.
3. **Robustez:** dado un cliente que envía JSON incorrecto o se desconecta,
   cuando llega otro cliente válido, el servidor continúa respondiendo.

## Archivos

- `src/kitchen_server.py`: servidor TCP y control de estado.
- `src/services/kitchen_client.py`: cliente, validación de respuestas y timeouts.
- `src/main.py`: despacho al finalizar el pago y acciones de cocina.
- `tests/test_kitchen_tcp.py`: casos automatizados.

La publicación de `READY` está integrada: después de confirmar `READY_ORDER` por TCP,
FastAPI guarda el estado y activa las notificaciones WebSocket mediante un evento
local. Reiniciar cocina pierde los pedidos; no se implementa recuperación persistente.

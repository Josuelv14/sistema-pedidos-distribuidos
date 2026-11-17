# ADR-005: Selección de mecanismos de comunicación

- **Estado:** Aceptado
- **Fecha:** [2026-11-16]
- **Decisores:** Equipo del sistema de pedidos

## Contexto

Un pedido pasa por varias etapas. El estudiante lo registra, caja confirma
el pago, cocina prepara el pedido y el estudiante recibe un aviso cuando puede
retirarlo. Cada etapa tiene necesidades de comunicación distintas.

## Decisión

| Tramo | Mecanismo | Motivo de la elección |
| --- | --- | --- |
| Estudiante → servicio de pedidos | REST | Permite crear y consultar pedidos mediante HTTP y JSON. La clave de idempotencia evita que un reintento de creación genere otro pedido. |
| Servicio de pedidos → caja | gRPC | Protocol Buffers define un contrato tipado para solicitar el pago y recibir su resultado. El servicio de pedidos espera la confirmación antes de enviar el pedido a cocina. |
| Servicio de pedidos → cocina | Sockets TCP | Permite demostrar cómo dos procesos intercambian mensajes JSON delimitados por saltos de línea. El protocolo controla el tiempo de espera y usa el ID para reconocer solicitudes repetidas. |
| Servicio de pedidos → estudiante | WebSockets | Permite que el servidor envíe el aviso al guardar `READY`. Si el estudiante se desconecta, puede volver a conectarse y consultar el estado guardado mediante el mensaje inicial. |

Los cuatro mecanismos participan en el flujo de un mismo pedido. El servicio
lo crea por REST, confirma el pago por gRPC y lo envía a cocina por TCP. Cuando
el operador ejecuta `POST /orders/{order_id}/ready`, el servicio confirma el
cambio con cocina por TCP, guarda `READY` y publica el aviso por WebSocket.

## Alternativas consideradas

- **gRPC como interfaz para el estudiante.** Ofrece un contrato tipado. REST
  encaja directamente con la interfaz HTTP y JSON prevista para crear y
  consultar pedidos.
- **REST o TCP para caja.** REST permitiría reutilizar HTTP y JSON. TCP
  requeriría definir el formato y los límites de cada mensaje. El ADR de caja
  eligió gRPC para definir las operaciones y sus mensajes en un contrato
  compartido.
- **REST, gRPC o Kafka para cocina.** El ADR de cocina considera REST y
  gRPC como opciones para la comunicación interna, y Kafka para desacoplar
  servicios mediante eventos. La implementación con TCP permite practicar el
  encuadre de mensajes y el manejo de conexiones con la infraestructura local
  del proyecto.
- **Consultas periódicas por REST para el aviso.** El estudiante podría
  consultar el estado a intervalos. Con WebSockets, el servidor puede avisar
  en cuanto guarda `READY` mientras la conexión siga abierta.

## Consecuencias

### Positivas

- El ID permite seguir el mismo pedido desde su creación hasta el aviso.
- El pago y las operaciones de cocina tienen respuesta y tiempo de espera.
- El aviso por WebSocket se envía de forma asíncrona. La preparación puede
  completarse mientras el estudiante está desconectado.

### Negativas y limitaciones

- Para la demostración se deben levantar los procesos de pedidos, caja y cocina.
- El equipo debe mantener el contrato gRPC, el protocolo TCP y los mensajes
  WebSocket.
- Los servicios guardan sus datos en memoria. Reiniciar un proceso elimina
  los datos que ese proceso conservaba.

## Referencias

- [ADR-001. API REST con FastAPI](adr-001-rest.md)
- [ADR-002. gRPC para caja y facturación](adr-002-grpc.md)
- [ADR-003. Sockets TCP entre pedidos y cocina](adr-003-sockets-tcp.md)
- [ADR-004. Notificaciones mediante WebSockets](adr-004-websockets.md)
- [Pruebas de WebSockets](prueba-websockets.md)

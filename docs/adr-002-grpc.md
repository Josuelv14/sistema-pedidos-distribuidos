# ADR 002: gRPC para caja y facturación

## Estado

Aceptado para la práctica.

## Contexto

El servicio de pedidos necesita solicitar el cobro a caja y conocer el resultado
antes de continuar con la preparación. Ambos servicios están desarrollados en
Python y se ejecutan como procesos separados.

## Decisión

Usar gRPC con Protocol Buffers para la comunicación entre pedidos y caja.
El contrato se encuentra en `src/proto/billing.proto`.

- `ProcessPayment` recibe el ID y el total del pedido. Devuelve la aprobación,
  el número de comprobante y el total.
- `GetSalesSummary` devuelve la cantidad de ventas y el total recaudado.

El pago es simulado y el comprobante es interno a la práctica. Los importes se
transmiten como texto y se procesan con `Decimal` para conservar los decimales.
Caja guarda las ventas en memoria y usa el ID del pedido para evitar cobros
duplicados. Si se repite el ID con otro total, rechaza la solicitud.

Pedidos espera como máximo dos segundos por cada llamada a caja. Si el pago se
aprueba, cambia el estado a `PAID`. Si ocurre un error gRPC, REST devuelve `503`
con el ID del pedido, que permanece en `PENDING`. El cliente puede reintentar
mediante `POST /orders/{order_id}/pay` o repetir la creación con la misma clave
de idempotencia y el mismo contenido.

## Alternativas consideradas

- REST: permitiría reutilizar HTTP y JSON, pero se eligió un contrato tipado
  para esta comunicación interna y para incorporar el mecanismo gRPC solicitado.
- Sockets TCP: exigirían definir manualmente el formato y los límites de los
  mensajes. Se reservan para la comunicación con cocina.

## Consecuencias

- El contrato define las operaciones y los mensajes compartidos entre servicios.
- Es necesario generar los módulos Python después de clonar el proyecto o
  modificar el archivo `.proto`.
- Caja debe estar ejecutándose para confirmar pagos.
- No hay reintentos automáticos; el reintento lo solicita el cliente.
- Al reiniciar caja se pierden ventas, comprobantes y protección contra cobros
  repetidos. La implementación está limitada a una demostración en memoria.
- La conexión local no usa TLS ni autenticación.

## Validación

`python -m unittest discover -s tests -v` ejecuta seis pruebas que cubren pagos,
resumen de ventas, solicitudes repetidas, importes inválidos, integración con
pedidos y desconexión de caja con recuperación del pago.

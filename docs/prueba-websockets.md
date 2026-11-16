# Pruebas de comportamiento de WebSockets

## Escenario de calidad

El estudiante pierde la conexión mientras su pedido está en preparación.
El sistema debe permitir que cocina complete el pedido y mostrar el estado
guardado cuando el estudiante vuelva a conectarse.

## Entorno

Prueba manual en Windows con Python 3.12.10. Los servicios de caja (gRPC),
cocina (sockets TCP) y FastAPI se ejecutaron localmente. Se usó Swagger para
las solicitudes REST y la consola de Chrome para observar los mensajes
WebSocket.

## Caso 1. Aviso con el estudiante conectado

1. Crear un pedido con `POST /orders/` y una clave `X-Idempotency-Key` nueva.
2. Abrir `/ws/orders/{order_id}` y esperar `order_status` con `PREPARING`.
3. Mantener la conexión abierta y ejecutar `POST /orders/{order_id}/ready`.
4. Revisar el mensaje que llega por WebSocket.

**Resultado esperado.** El cliente recibe `order_ready` con estado `READY`.

**Resultado observado.** Para el pedido `jzqbH2G6`, la solicitud `POST /ready`
respondió HTTP 200 con estado `READY`. El navegador recibió `order_ready`
con el mismo ID y estado `READY`. El servidor cerró la conexión con código
`1000`.

## Caso 2. Desconexión y reconexión antes de recibir el aviso

1. Crear otro pedido con una clave `X-Idempotency-Key` nueva.
2. Abrir el WebSocket del pedido y esperar `order_status` con `PREPARING`.
3. Ejecutar `ws.close()` y esperar que la consola confirme el cierre.
4. Con el cliente desconectado, ejecutar `POST /orders/{order_id}/ready`.
5. Volver a abrir el WebSocket para el mismo ID.

**Resultado esperado.** Cocina puede completar el pedido durante la
desconexión. Al regresar, el cliente recibe `order_status` con `READY`.

**Resultado observado.** El pedido `iKGKmsr9` estaba en `PREPARING` antes
del cierre. Después de ejecutar `POST /ready` y volver a conectar, el
navegador recibió `order_status` con estado `READY` y el mismo ID.

## Cliente usado para la prueba

Desde la consola del navegador, en la página local de Swagger, definir:

~~~javascript
globalThis.conectarPedido = (id) => {
  const socket = new WebSocket(`ws://${location.host}/ws/orders/${id}`);
  socket.onmessage = ({ data }) => console.log(JSON.parse(data));
  socket.onclose = ({ code }) => console.log("Conexión cerrada", code);
  return socket;
};
~~~

Para cada prueba, ejecutar `globalThis.ws = conectarPedido("ID_REAL")`
reemplazando `ID_REAL` por el ID devuelto por Swagger.
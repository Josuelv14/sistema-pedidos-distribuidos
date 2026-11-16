# Prueba de comportamiento: caja no disponible

## Objetivo

Comprobar que pedidos responde de forma controlada cuando el servicio interno
de caja no está disponible y permite completar el pago al recuperar el servicio.

## Escenario de calidad propuesto: disponibilidad

Este escenario debe incorporarse y priorizarse con los escenarios del grupo.

| Elemento | Descripción |
| --- | --- |
| Fuente | Estudiante que solicita un pedido o reintenta su pago. |
| Estímulo | Caja está detenida al solicitar el pago por gRPC. |
| Entorno | API REST activa y caja fuera de servicio durante la prueba local. |
| Elemento afectado | Comunicación entre pedidos y caja. |
| Respuesta esperada | REST devuelve un error controlado, conserva el pedido pendiente y permite reintentar al recuperar caja. |
| Medida | La llamada gRPC tiene un plazo configurado de dos segundos; al recuperar caja, el mismo ID puede pasar a `PAID`. |

## Preparación y procedimiento

Con los archivos gRPC generados según el README, ejecutar en terminales separadas:

```powershell
python -m src.billing_server
```

```powershell
python -m uvicorn src.main:app --reload
```

Desde `http://127.0.0.1:8000/docs`:

1. Crear un pedido con caja activa para comprobar el flujo normal.
2. Detener solo caja con `Ctrl+C`, manteniendo REST activo.
3. Enviar `POST /orders/` con `X-Idempotency-Key: prueba-caja-2` y este cuerpo:

```json
{
  "product": "Cafe",
  "quantity": 2,
  "unit_price": 3.50
}
```

4. Copiar el ID del error y solicitar `POST /orders/{order_id}/pay` mientras caja
   sigue detenida.
5. Reiniciar caja y repetir el pago con el mismo ID, sin crear otro pedido.

## Resultados observados

Ejecución manual realizada por Emanuel el 15 de noviembre de 2026 desde Swagger.
Las respuestas fueron compartidas durante la comprobación del sistema.

| Paso | Resultado real |
| --- | --- |
| Creación con caja activa y clave `prueba-caja-1` | HTTP `201`, pedido `EDDC7zqr`, total `7.0`, estado `PAID`. |
| Creación con caja detenida y clave `prueba-caja-2` | HTTP `503`, mensaje de fallo de pago e ID `Mw8doVaN`. |
| Reintento de pago sin recuperar caja | HTTP `503` para el mismo pedido `Mw8doVaN`. |
| Reintento después de reiniciar caja | HTTP `200`, mismo ID `Mw8doVaN`, total `7.0`, estado `PAID`. |

Respuesta al crear el pedido con caja detenida:

```json
{
  "detail": {
    "message": "No se pudo confirmar el pago con caja. Reintente el pago.",
    "order_id": "Mw8doVaN"
  }
}
```

Respuesta al completar el pago después de reiniciar caja:

```json
{
  "product": "Cafe",
  "quantity": 2,
  "unit_price": "3.5",
  "id": "Mw8doVaN",
  "total": "7.0",
  "status": "PAID"
}
```

No se registró una medición manual del tiempo de respuesta ni una respuesta GET
intermedia del estado `PENDING`. La conservación de ese estado y los reintentos
sin duplicar ventas están comprobados en las pruebas automatizadas de
`tests/test_billing.py`, ejecutadas con seis resultados satisfactorios:

```powershell
python -m unittest discover -s tests -v
```

## Conceptos para explicar en la defensa

- La llamada gRPC es un RPC síncrono: pedidos espera la respuesta de otro proceso.
- El fallo de caja es un fallo parcial del sistema distribuido. REST sigue
  atendiendo y traduce el error gRPC a una respuesta HTTP `503`.
- El plazo de dos segundos limita la espera de la llamada. No se interpreta
  una falta de respuesta como un pago aprobado.
- El reintento usa el mismo ID del pedido. Caja conserva el comprobante por ID
  para evitar ventas repetidas mientras su proceso permanece activo.
- Los datos están en memoria. Reiniciar caja pierde su registro de ventas;
  esta prueba demuestra recuperación de un pedido que no se había cobrado,
  no persistencia de pagos anteriores ni tolerancia completa a reinicios.

El integrante debe revisar este registro y explicar el resultado con los
conceptos del capítulo antes de usarlo en la entrega.

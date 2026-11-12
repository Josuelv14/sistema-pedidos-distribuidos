# ADR-001: API REST con FastAPI

- **Estado:** Aceptado
- **Fecha:** 2026-11-12
- **Decisores:** Equipo del sistema de pedidos

## Contexto

El sistema requiere una interfaz sencilla para crear pedidos, consultarlos y
actualizar su estado. Los consumidores deben poder integrarse usando HTTP y
JSON, y los reintentos de red de una solicitud de creación no deben producir
pedidos duplicados. Para la primera entrega, el almacenamiento será en memoria;
la integración gRPC se desarrollará de forma complementaria.

## Decisión

Se adopta una API REST implementada con FastAPI. Los pedidos se exponen mediante
los recursos `/orders/`, con operaciones `POST`, `GET` y `PATCH`. Los modelos
Pydantic validan las solicitudes y respuestas. Cada pedido recibe un
identificador alfanumérico de ocho caracteres, y el total se calcula a partir
de la cantidad y el precio unitario.

La creación requiere el encabezado `X-Idempotency-Key`. Para una clave ya
utilizada con el mismo contenido se devuelve el pedido original; su
reutilización con un contenido distinto produce `409 Conflict`. El estado del
pedido se limita a `PENDING`, `PREPARING`, `READY` y `PAID`.

## Alternativas consideradas

1. **Frameworks ASGI de bajo nivel:** ofrecen flexibilidad, pero exigen
   implementar manualmente más validación y documentación.
2. **gRPC como única interfaz:** proporciona contratos tipados eficientes, pero
   no satisface tan directamente el acceso HTTP/JSON requerido para esta
   primera interfaz de pedidos.
3. **Frameworks REST alternativos:** son viables, pero FastAPI integra
   validación tipada y generación OpenAPI con poca configuración.

## Consecuencias

### Positivas

- Los consumidores pueden usar HTTP estándar y JSON.
- La validación y la documentación OpenAPI se generan desde los modelos.
- La clave idempotente evita duplicados ante reintentos mientras el proceso
  permanece activo.

### Negativas y limitaciones

- El almacenamiento y las claves de idempotencia se pierden al reiniciar el
  servidor y no se comparten entre múltiples instancias.
- La idempotencia está acotada al proceso y no sustituye una solución
  persistente distribuida.
- Se mantiene gRPC como posible interfaz complementaria, no como sustituto de
  esta API REST.

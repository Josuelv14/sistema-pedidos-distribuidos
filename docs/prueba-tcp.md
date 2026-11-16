# Pruebas de comportamiento — Sockets TCP de cocina

**Responsable:** Esteban Hernandez.

**Asistencia IA:** Casos y redacción preliminar generados con ayuda de ChatGPT.

## Cómo ejecutar

Desde la raíz, después de instalar dependencias y generar código gRPC:

```powershell
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. src/proto/billing.proto
python -m unittest discover -s tests -p "test_kitchen_tcp.py" -v
```

El módulo ejecuta nueve pruebas: recepción y preparación, reintento idempotente,
conflicto de ID, JSON inválido, desconexión de cliente, servidor no disponible,
consulta inexistente, secuencia API → pago simulado → cocina → READY y fallo de
cocina conservando `PAID` con reintento.

## Escenario A — Reintento de mensaje TCP

- **Atributo:** confiabilidad/idempotencia.
- **Estímulo:** enviar dos veces `CREATE_ORDER` con el mismo ID, producto y cantidad.
- **Esperado:** primera respuesta `duplicate: false`; segunda `duplicate: true`;
  solo una entrada en cocina.
- **Evidencia real:**

![Prueba de idempotencia TCP](assets/Caso_A.png)

*Figura 1. Ejecución de las pruebas de idempotencia del servicio TCP.*

## Escenario B — Cocina no responde

- **Atributo:** disponibilidad.
- **Estímulo:** detener el servicio TCP y crear un pedido con caja disponible.
- **Esperado:** `503`, pedido en `PAID`; al iniciar cocina y reintentar
  `POST /orders/{id}/dispatch`, cambia a `PREPARING` sin cobrar de nuevo.
- **Evidencia real:**

![Error 503 con cocina desconectada](assets/Caso_B%20(1).png)

*Figura 2. Respuesta HTTP 503 cuando el servicio de cocina no está disponible.*

![Recuperación del servicio de cocina](assets/Caso_B%20(2).png)

*Figura 3. Reintento del despacho y actualización del pedido a PREPARING.*

## Escenario C — Cliente se desconecta

- **Atributo:** robustez/tolerancia a fallos.
- **Estímulo:** cortar la conexión mientras se envía un JSON incompleto.
- **Esperado:** el servidor continúa activo y acepta el pedido siguiente.
- **Evidencia real:**

![Desconexión inesperada del cliente](assets/Caso_C%20(1).png)

*Figura 4. Simulación de desconexión durante el envío de un mensaje JSON incompleto.*

![Servidor TCP continúa funcionando](assets/Caso_C%20(2).png)

*Figura 5. Respuesta del servidor TCP a una nueva conexión después de la desconexión.*

## Resultado de verificación preliminar

En una reconstrucción local de los módulos publicados en `main`, nueve pruebas
de este módulo pasaron con la respuesta de caja simulada en los casos de integración.
**No equivale a la ejecución del repositorio completo del grupo.** Antes de
entregar, ejecutar en el equipo local y sustituir las evidencias pendientes.


## Interpretación de resultados

TCP entrega un flujo de bytes y no preserva por sí mismo los límites de mensaje:
por eso se usa `\n` y límite de 4096 bytes. Un timeout evita la espera infinita.
La deduplicación se realiza por ID en la lógica de cocina, no es una función
nativa de TCP. Estas medidas reducen fallos, pero los datos en memoria
se pierden si el servicio reinicia.

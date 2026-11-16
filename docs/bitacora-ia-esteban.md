# Bitácora de uso de IA — Integrante 3

**Proyecto:** Sistema de pedidos distribuido  
**Responsabilidad:** Implementación del microservicio de cocina mediante Sockets TCP  
**Herramienta utilizada:** ChatGPT  
**Rama de desarrollo:** `feature/sockets-cocina/esteban`

## 1. Registro de consultas y asistencia de IA

| Quién consultó | Consulta realizada | Qué respondió la herramienta | Qué hizo el integrante |
| --- | --- | --- | --- |
| Integrante 3 | ¿Cómo diseñar un microservicio de cocina basado en Sockets TCP que permita la comunicación entre procesos independientes, utilizando mensajes JSON y controlando conexiones simultáneas? | Propuso implementar un servidor con `socketserver.ThreadingTCPServer`, utilizando mensajes JSON delimitados por saltos de línea y un protocolo de petición-respuesta. | Incorporó el servidor en `src/kitchen_server.py`, definiendo operaciones para registrar, consultar y actualizar pedidos. |
| Integrante 3 | ¿Qué mecanismos de idempotencia y validación pueden implementarse en un servidor TCP para evitar pedidos duplicados cuando el cliente reintenta una solicitud después de una interrupción de conexión? | Recomendó identificar cada pedido mediante un ID único, comprobar los registros existentes y rechazar solicitudes que reutilicen un identificador con información diferente. | Implementó controles de duplicación y conflictos, manteniendo los estados `PREPARING` y `READY` en memoria. |
| Integrante 3 | ¿Cómo desarrollar un cliente TCP reutilizable que gestione tiempos de espera, errores de conexión, respuestas inválidas y excepciones específicas sin comprometer la estabilidad del servicio REST? | Propuso encapsular la comunicación mediante una clase `KitchenClient`, estableciendo timeouts y excepciones diferenciadas para problemas de disponibilidad, protocolo y rechazo de solicitudes. | Incorporó `src/services/kitchen_client.py` y utilizó el cliente para comunicar la API REST con cocina. |
| Integrante 3 | ¿Cómo integrar REST, gRPC y Sockets TCP en un mismo flujo de pedidos, garantizando que un fallo de cocina después de un pago aprobado no provoque un segundo cobro? | Planteó conservar el estado `PAID` después de confirmar el pago, enviar el pedido a cocina mediante TCP y habilitar un mecanismo de reintento independiente del procesamiento de caja. | Adaptó `src/main.py` para despachar pedidos pagados, gestionar errores `503` y permitir reintentos mediante `/orders/{order_id}/dispatch`. |
| Integrante 3 | ¿Cómo verificar la confiabilidad de un protocolo TCP mediante pruebas automatizadas que contemplen solicitudes duplicadas, mensajes JSON inválidos, desconexiones inesperadas y servicios temporalmente no disponibles? | Propuso pruebas unitarias y de integración utilizando `unittest`, servidores TCP temporales y simulación de dependencias externas. | Incorporó `tests/test_kitchen_tcp.py` y ejecutó nueve pruebas, todas finalizadas correctamente. |
| Integrante 3 | ¿Cómo identificar y resolver incompatibilidades entre pruebas existentes de facturación gRPC y un nuevo flujo que incorpora el despacho automático de pedidos mediante TCP? | Identificó que las pruebas anteriores asumían que el flujo terminaba en `PAID` y recomendó aislar el despacho TCP mediante simulaciones en las pruebas de facturación. | Analizó los errores de integración detectados al ejecutar las 15 pruebas del proyecto y revisó una propuesta para adaptar las pruebas existentes. |
| Integrante 3 | ¿Cómo documentar las decisiones arquitectónicas, los escenarios de calidad y las limitaciones de un microservicio TCP integrado en una arquitectura distribuida? | Propuso un registro ADR con decisiones técnicas, alternativas, ventajas, limitaciones y escenarios relacionados con disponibilidad, confiabilidad y robustez. | Preparó la documentación del componente TCP y actualizó la descripción de la arquitectura, diferenciando los servicios implementados de la integración WebSockets pendiente. |

## 2. Verificación de resultados

Durante el desarrollo se realizaron pruebas automatizadas para comprobar el funcionamiento de los mecanismos de comunicación y la integración entre los servicios REST, gRPC y Sockets TCP.

Inicialmente, las nueve pruebas específicas del servicio de cocina finalizaron correctamente. Sin embargo, al ejecutar las pruebas completas del proyecto, se detectaron dos errores relacionados con la integración del despacho TCP en las pruebas existentes de facturación gRPC.

Con apoyo de la herramienta de inteligencia artificial, se identificó que las pruebas anteriores asumían que los pedidos finalizaban en el estado `PAID`, mientras que el nuevo flujo incorporaba su envío automático a cocina y la transición a `PREPARING`.

Para solucionar esta incompatibilidad, se adaptaron las pruebas de facturación mediante la simulación del despacho TCP, permitiendo verificar el procesamiento de pagos sin depender de la disponibilidad del servicio de cocina.

Después de aplicar las correcciones, se ejecutó nuevamente el conjunto completo de pruebas mediante el comando:

`python -m unittest discover -s tests -v`

**Resultado final: 15 pruebas ejecutadas correctamente, sin errores ni fallos.**

Este resultado permitió comprobar el funcionamiento de las pruebas de facturación gRPC, la comunicación TCP, los mecanismos de idempotencia, el manejo de excepciones y los escenarios automatizados de integración entre servicios.

## 3. Reflexión sobre el uso de IA

La inteligencia artificial fue utilizada como herramienta de apoyo durante el diseño, implementación, integración y verificación del microservicio de cocina mediante Sockets TCP.

Durante el desarrollo se presentaron dificultades relacionadas con la aplicación de parches sobre archivos existentes y la compatibilidad entre las pruebas de facturación y la nueva integración TCP. Estas situaciones requirieron revisar el código, identificar las causas de los errores y adaptar las soluciones propuestas a la estructura real del proyecto.

Como resultado, se consiguió integrar el servicio de cocina con los componentes REST y gRPC, además de completar satisfactoriamente las 15 pruebas automatizadas del proyecto.

# Bitácora de uso de IA — Emanuel

**Responsable:** Emanuel  
**Parte del proyecto:** Caja y facturación mediante gRPC  
**Herramienta:** Codex (OpenAI)

## Registro de consultas

| Quién consultó | Consulta | Respuesta de la herramienta | Aplicación |
| --- | --- | --- | --- |
| Emanuel | ¿Cómo definir la comunicación gRPC entre pedidos y caja? | Proporcionó una propuesta de contrato y estructura del cliente y servidor. | Se utilizó como base para conectar los servicios y comprobar el pago desde REST. |
| Emanuel | ¿Cómo evitar pagos duplicados por reintentos? | Sugirió registrar el pago por ID del pedido y reutilizar el comprobante. | Se incorporó el control y se verificó con pruebas de solicitudes repetidas. |
| Emanuel | ¿Cómo manejar una desconexión de caja? | Propuso limitar la espera, conservar el pedido pendiente y permitir reintentar. | Apagué caja y observé el error `503`; al reiniciarla, recuperé el pago con respuesta `200` y estado `PAID`. |
| Emanuel | ¿Cómo verificar y documentar la integración? | Ayudó con pruebas automatizadas, organización del ADR y revisión del mapa de servicios. | Se ejecutaron las pruebas y se actualizaron los documentos según el flujo integrado. |

## Reflexión

La IA sirvió de apoyo para trabajar la comunicación entre servicios y sus fallos.
Sus respuestas necesitaron comprobación: inicialmente dio por completa la entrega
sin contrastar todos los requisitos del PDF y sugirió capturas que no eran
obligatorias. Las pruebas permitieron comprobar el comportamiento real del sistema.

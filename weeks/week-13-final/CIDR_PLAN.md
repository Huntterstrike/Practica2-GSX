# CIDR Plan — Propuesta (Week 12 / 13)

## Rango global\- `10.0.0.0/16`

## Subredes propuestas\- `10.0.1.0/24` → Development (dev)
- `10.0.2.0/24` → Staging
- `10.0.3.0/24` → Production
- `10.0.10.0/24` → Partners / VPN

## Justificación
- /24 por entorno es suficiente para prácticas y evita solapamientos en entornos de laboratorio.
- Separación facilita aplicar reglas de perímetro, NAT y VPN.
- En Kubernetes la segmentación se aplica habitualmente por namespace/labels; el plan CIDR es útil para la conectividad entre sedes y reglas a nivel de red física.

## Notas
- Para un despliegue real, ajustar tamaño de subred según número de hosts y servicios.
- Mantener documentación de asignación IP y evitar solapamientos con redes externas.

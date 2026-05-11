## ADDED Requirements

### Requirement: Polygon totals include Lighthouse actors after topology changes
The system SHALL refresh the right-bottom VTK polygon-count display whenever Lighthouse actors are added or removed, so totals include the current Lighthouse geometry.

#### Scenario: Polygon totals update after Lighthouse add
- **WHEN** tracking is enabled and one or more Lighthouse actors are added to the VTK scene
- **THEN** the right-bottom polygon-count display is recomputed and includes the added Lighthouse polygons

#### Scenario: Polygon totals update after Lighthouse remove
- **WHEN** tracking is enabled and one or more Lighthouse actors are removed from the VTK scene
- **THEN** the right-bottom polygon-count display is recomputed and excludes the removed Lighthouse polygons

### Requirement: Tracking disable cleanup updates polygon totals
The system SHALL recompute the right-bottom VTK polygon-count display after removing all Lighthouse actors during tracking disable.

#### Scenario: Polygon totals update after tracking disable cleanup
- **WHEN** tracking is disabled and all Lighthouse actors are removed from VTK
- **THEN** the right-bottom polygon-count display is refreshed to reflect a scene without Lighthouse polygons

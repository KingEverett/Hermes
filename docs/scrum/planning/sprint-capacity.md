# Sprint Capacity Planning

## Team Configuration
- **Team Size**: 3 developers
- **Sprint Length**: 2 weeks
- **Capacity Factor**: 70% (accounting for meetings, bugs, overhead)
- **Target Velocity**: 13-14 points per sprint

## Velocity Calculations

### Individual Capacity
- **Available Hours per Sprint**: 80 hours (2 weeks × 40 hours)
- **Effective Hours**: 56 hours (80 × 70% capacity)
- **Team Capacity per Sprint**: 168 hours (56 × 3 developers)

### Story Point Velocity
- **Historical Velocity**: Not available (new project)
- **Estimated Velocity**: 13-14 points per sprint
- **Total Project Points**: 108 points
- **Estimated Sprints**: 8 sprints

## Sprint Allocation

| Sprint | Epic Focus | Story Points | Key Deliverables |
|--------|------------|--------------|------------------|
| 1 | Epic 1 Foundation | 8 | Infrastructure, Data Models |
| 2 | Epic 1 Core | 18 | Parser, Markdown Generator |
| 3 | Epic 2 Research | 21 | Version Analysis, API Config |
| 4 | Epic 2 Integration | 15 | NVD Integration |
| 5 | Epic 3 Visualization | 18 | Network Graph, Controls |
| 6 | Epic 3 Interface | 8 | Three-Panel Layout |
| 7 | Epic 4 CLI | 13 | CLI Tool Implementation |
| 8 | Integration | 7 | Testing, Bug Fixes, Polish |

## Risk Factors

### Capacity Risks
- **New Technology Learning**: D3.js, FastAPI learning curve
- **External Dependencies**: NVD API reliability
- **Integration Complexity**: Cross-epic dependencies

### Mitigation Strategies
- **Buffer Time**: 30% capacity buffer built into estimates
- **Risk Stories**: Identified high-risk stories for early attention
- **Parallel Work**: Some preparation work can happen in parallel

## Velocity Monitoring

### Metrics to Track
- **Story Points Completed per Sprint**
- **Story Completion Rate**
- **Defect Rate**
- **Velocity Trend**

### Adjustment Triggers
- **Velocity < 10 points**: Investigate blockers
- **Velocity > 16 points**: Check for under-estimation
- **Trend Decline**: Address team impediments
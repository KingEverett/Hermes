# Performance Optimization

## Caching Strategy

```python
# Redis caching implementation
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=86400)  # 24 hours
async def get_cve_details(cve_id: str):
    # Expensive API call
    return await nvd_service.fetch_cve(cve_id)
```

## Database Optimization

```sql
-- Materialized view for project statistics
CREATE MATERIALIZED VIEW project_statistics AS
SELECT 
    p.id as project_id,
    COUNT(DISTINCT h.id) as host_count,
    COUNT(DISTINCT s.id) as service_count,
    COUNT(DISTINCT v.id) as vulnerability_count,
    SUM(CASE WHEN v.severity = 'critical' THEN 1 ELSE 0 END) as critical_count
FROM projects p
LEFT JOIN hosts h ON p.id = h.project_id
LEFT JOIN services s ON h.id = s.host_id
LEFT JOIN service_vulnerabilities sv ON s.id = sv.service_id
LEFT JOIN vulnerabilities v ON sv.vulnerability_id = v.id
GROUP BY p.id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW project_statistics;
```

# Graph Database Optimization Guide

## 1. Schema Design Best Practices

### Efficient Node Labels
```cypher
// Bad: Multiple labels for categorization
CREATE (:Content:Article:Tech:Featured {title: "GraphDB Best Practices"})

// Good: Use properties for categorization
CREATE (:Content {
    type: "article",
    category: "tech",
    featured: true,
    title: "GraphDB Best Practices"
})
```

### Relationship Design
```cypher
// Bad: Using properties to differentiate relationship types
CREATE (u:User)-[:INTERACTION {type: "LIKE"}]->(c:Content)

// Good: Use specific relationship types
CREATE (u:User)-[:LIKED]->(c:Content)
```

## 2. Indexing Strategies

### Single Property Indexes
```cypher
// Create index for frequently queried properties
CREATE INDEX user_email IF NOT EXISTS
FOR (u:User) ON (u.email);

// Create unique constraint and index
CREATE CONSTRAINT user_id IF NOT EXISTS
FOR (u:User) ASSERT u.id IS UNIQUE;
```

### Composite Indexes
```cypher
// Create composite index for combined property searches
CREATE INDEX content_type_date IF NOT EXISTS
FOR (c:Content) ON (c.type, c.published_date);

// Index for relationship properties
CREATE INDEX transfer_date IF NOT EXISTS
FOR ()-[t:TRANSFER]-() ON (t.timestamp);
```

## 3. Query Optimization Techniques

### Using Parameters
```cypher
// Bad: Hard-coded values
MATCH (u:User {email: "user@example.com"})
RETURN u;

// Good: Use parameters
MATCH (u:User {email: $email})
RETURN u;
```

### Efficient Path Finding
```cypher
// Bad: Unbounded variable length path
MATCH p=(start:User)-[:FOLLOWS*]->(end:User)
RETURN p;

// Good: Bounded path length with direction
MATCH p=(start:User)-[:FOLLOWS*1..3]->(end:User)
RETURN p;
```

### Pattern Optimization
```cypher
// Bad: Multiple separate matches
MATCH (u:User {id: $id})
MATCH (u)-[:VIEWED]->(c1:Content)
MATCH (u)-[:LIKED]->(c2:Content)
RETURN c1, c2;

// Good: Combined pattern matching
MATCH (u:User {id: $id})
      -[:VIEWED|LIKED]->(content:Content)
RETURN content;
```

## 4. Memory Management

### Batch Processing
```cypher
// Process large datasets in chunks
CALL apoc.periodic.iterate(
    "MATCH (u:User) RETURN u",
    "WITH u
     OPTIONAL MATCH (u)-[:VIEWED]->(c:Content)
     WITH u, count(c) as views
     SET u.view_count = views",
    {batchSize: 1000, parallel: true}
);
```

### Result Limiting
```cypher
// Bad: Return all results
MATCH (c:Content)
RETURN c;

// Good: Use pagination
MATCH (c:Content)
RETURN c
SKIP $offset
LIMIT $pageSize;
```

## 5. Performance Monitoring

### Query Planning
```cypher
// Analyze query performance
PROFILE
MATCH (u:User {id: $id})
      -[:FOLLOWS*1..2]->
      (follower:User)
RETURN follower;

// Get query plan explanation
EXPLAIN
MATCH (c:Content)
WHERE c.published_date > $date
RETURN c;
```

### Statistics Updates
```cypher
// Update statistics for better query planning
CALL db.stats.retrieve('RELATIONSHIPS');
CALL db.stats.retrieve('NODES');
```

## 6. Common Anti-patterns to Avoid

### Relationship Anti-patterns
```cypher
// Bad: Using intermediate nodes for relationship properties
CREATE (u1:User)-[:FOLLOWS]->(f:Following {since: timestamp()})-[:TO]->(u2:User)

// Good: Use relationship properties
CREATE (u1:User)-[:FOLLOWS {since: timestamp()}]->(u2:User)
```

### Query Anti-patterns
```cypher
// Bad: Collecting all nodes then filtering
MATCH (n:User)
WITH collect(n) as users
UNWIND users as user
WHERE user.age > 25
RETURN user;

// Good: Filter during pattern matching
MATCH (user:User)
WHERE user.age > 25
RETURN user;
```

## 7. Caching Strategies

### Result Caching
```cypher
// Cache frequently accessed data
CALL apoc.cache.set(
    'popular_content',
    'MATCH (c:Content) 
     WHERE c.views > 1000 
     RETURN c',
    3600  // Cache for 1 hour
);

// Retrieve cached results
CALL apoc.cache.get('popular_content');
```

### Warm-up Queries
```cypher
// Run queries to warm up cache
CALL apoc.periodic.submit(
    'cache-warmup
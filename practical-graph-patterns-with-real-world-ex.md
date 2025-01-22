# Practical Graph Patterns with Real-World Examples

## 1. E-commerce Recommendation System

### DOT Graph
```dot
digraph ECommerce {
    // Users
    user1 [label="User", name="John", age="25"]
    user2 [label="User", name="Mary", age="30"]
    
    // Products
    prod1 [label="Product", name="Laptop", category="Electronics", price="1200"]
    prod2 [label="Product", name="Headphones", category="Electronics", price="200"]
    prod3 [label="Product", name="Mouse", category="Electronics", price="50"]
    
    // Purchase relationships
    user1 -> prod1 [label="PURCHASED", date="2024-01-15"]
    user1 -> prod2 [label="PURCHASED", date="2024-01-16"]
    user2 -> prod2 [label="PURCHASED", date="2024-01-10"]
    user2 -> prod3 [label="PURCHASED", date="2024-01-12"]
    
    // Product relationships
    prod1 -> prod2 [label="FREQUENTLY_BOUGHT_WITH", strength="0.8"]
    prod2 -> prod3 [label="FREQUENTLY_BOUGHT_WITH", strength="0.6"]
}
```

### Neo4j Queries

1. Find products frequently bought together:
```cypher
// Find direct product associations
MATCH (p1:Product)<-[:PURCHASED]-(u:User)-[:PURCHASED]->(p2:Product)
WHERE p1 <> p2
WITH p1, p2, count(*) as frequency
CREATE (p1)-[:FREQUENTLY_BOUGHT_WITH {strength: frequency * 1.0 / 
    // Normalize by total purchases
    MATCH (p:Product)<-[:PURCHASED]-()
    RETURN count(*)
}]->(p2)

// Get recommendations for a product
MATCH (p:Product {name: "Laptop"})-[r:FREQUENTLY_BOUGHT_WITH]->(recommended)
RETURN recommended.name, r.strength
ORDER BY r.strength DESC
```

2. Personalized recommendations:
```cypher
// Based on user's purchase history
MATCH (u:User {name: "John"})-[:PURCHASED]->(bought:Product)
MATCH (bought)-[:FREQUENTLY_BOUGHT_WITH]->(recommended:Product)
WHERE NOT (u)-[:PURCHASED]->(recommended)
RETURN recommended.name, count(*) as strength
ORDER BY strength DESC
```

## 2. Social Network Friend Suggestions

### DOT Graph
```dot
digraph SocialNetwork {
    // Users
    alice [label="User", name="Alice", interests="tech,music"]
    bob [label="User", name="Bob", interests="tech,sports"]
    charlie [label="User", name="Charlie", interests="music,sports"]
    david [label="User", name="David", interests="tech,music"]
    
    // Friendship relationships
    alice -> bob [label="FRIENDS", since="2023"]
    bob -> charlie [label="FRIENDS", since="2023"]
    charlie -> david [label="FRIENDS", since="2024"]
    
    // Interest groups
    techGroup [label="Group", name="TechLovers"]
    musicGroup [label="Group", name="MusicFans"]
    
    // Group memberships
    alice -> techGroup [label="MEMBER_OF"]
    bob -> techGroup [label="MEMBER_OF"]
    alice -> musicGroup [label="MEMBER_OF"]
    david -> musicGroup [label="MEMBER_OF"]
}
```

### Neo4j Queries

1. Find friends of friends:
```cypher
// Basic friend suggestions
MATCH (user:User {name: "Alice"})-[:FRIENDS]->(friend)-[:FRIENDS]->(fof:User)
WHERE NOT (user)-[:FRIENDS]->(fof)
AND user <> fof
RETURN fof.name, count(*) as common_friends
ORDER BY common_friends DESC

// Friend suggestions with common interests
MATCH (user:User {name: "Alice"})-[:FRIENDS]->(friend)-[:FRIENDS]->(fof:User)
WHERE NOT (user)-[:FRIENDS]->(fof)
AND user <> fof
WITH fof, count(*) as common_friends,
     [x in split(user.interests, ',') WHERE x in split(fof.interests, ',')] as shared_interests
RETURN fof.name, common_friends, shared_interests, size(shared_interests) as interest_count
ORDER BY common_friends DESC, interest_count DESC
```

2. Group-based suggestions:
```cypher
// Find users in same groups
MATCH (user:User {name: "Alice"})-[:MEMBER_OF]->(group:Group)<-[:MEMBER_OF]-(other:User)
WHERE NOT (user)-[:FRIENDS]->(other)
AND user <> other
RETURN other.name, collect(group.name) as common_groups
ORDER BY size(common_groups) DESC
```

## 3. Project Dependency Graph

### DOT Graph
```dot
digraph ProjectDependencies {
    // Services
    api [label="Service", name="API", version="1.0"]
    auth [label="Service", name="Auth", version="2.0"]
    db [label="Service", name="Database", version="3.0"]
    cache [label="Service", name="Cache", version="1.5"]
    
    // Dependencies
    api -> auth [label="DEPENDS_ON", required="true"]
    api -> db [label="DEPENDS_ON", required="true"]
    api -> cache [label="DEPENDS_ON", required="false"]
    auth -> db [label="DEPENDS_ON", required="true"]
    
    // Health status
    api -> healthCheck1 [label="HEALTH_STATUS", status="healthy"]
    auth -> healthCheck2 [label="HEALTH_STATUS", status="degraded"]
}
```

### Neo4j Queries

1. Dependency analysis:
```cypher
// Find critical path (required dependencies)
MATCH path = (service:Service)-[:DEPENDS_ON*]->(dependency:Service)
WHERE service.name = "API"
AND ALL(r IN relationships(path) WHERE r.required = "true")
RETURN path

// Find service impact
MATCH (impacted:Service)-[:DEPENDS_ON*]->(service:Service {name: "Database"})
RETURN impacted.name as affected_service,
       length(path) as dependency_depth
ORDER BY dependency_depth
```

2. Health monitoring:
```cypher
// Check system health
MATCH (s:Service)-[h:HEALTH_STATUS]->(check)
WITH s, h.status as status
MATCH (s)<-[:DEPENDS_ON*0..]-(dependent:Service)
WHERE h.status <> "healthy"
RETURN s.name as problem_service,
       collect(DISTINCT dependent.name) as affected_services
```

## 4. Knowledge Graph

### DOT Graph
```dot
digraph Knowledge {
    // Concepts
    python [label="Concept", name="Python", type="Language"]
    django [label="Concept", name="Django", type="Framework"]
    webdev [label="Concept", name="Web Development", type="Domain"]
    database [label="Concept", name="Database", type="Technology"]
    
    // Relationships
    python -> django [label="USED_IN"]
    django -> webdev [label="PART_OF"]
    django -> database [label="USES"]
    
    // Learning paths
    beginner [label="Path", name="Beginner"]
    intermediate [label="Path", name="Intermediate"]
    
    // Path components
    beginner -> python [label="CONTAINS", order="1"]
    beginner -> django [label="CONTAINS", order="2"]
    intermediate -> django [label="CONTAINS", order="1"]
    intermediate -> database [label="CONTAINS", order="2"]
}
```

### Neo4j Queries

1. Find learning paths:
```cypher
// Get complete learning path
MATCH path = (p:Path {name: "Beginner"})-[r:CONTAINS]->(c:Concept)
RETURN c.name as concept,
       r.order as learn_order
ORDER BY r.order

// Find prerequisites
MATCH (concept:Concept {name: "Django"})<-[:USED_IN]-(prereq:Concept)
RETURN prereq.name as prerequisite
```

2. Knowledge exploration:
```cypher
// Find related concepts
MATCH (c:Concept {name: "Django"})-[r]->(related:Concept)
RETURN type(r) as relationship,
       related.name as related_concept

// Find concept usage
MATCH (c:Concept)-[:USED_IN|PART_OF|USES*1..3]->(usage)
WHERE c.name = "Python"
RETURN usage.name as used_in,
       length(path) as distance
```

Would you like me to:
1. Add more specific examples for any of these patterns?
2. Show more complex queries?
3. Explain how to optimize these queries for better performance?
4. Add more real-world use cases?

I've created a detailed guide with real-world examples. Each example shows:

How to structure the data in DOT format
How to query it in Neo4j
Common use cases and patterns
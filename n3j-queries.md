# Detailed Query Patterns in DOT and Neo4j

## 1. Finding Connected Nodes (Friend Network Example)

### DOT Representation
```dot
digraph FriendNetwork {
    // Define people
    alice [label="Person", name="Alice"]
    bob [label="Person", name="Bob"]
    charlie [label="Person", name="Charlie"]
    david [label="Person", name="David"]

    // Define friendships
    alice -> bob [label="FRIENDS"]
    bob -> charlie [label="FRIENDS"]
    charlie -> david [label="FRIENDS"]
    alice -> david [label="FRIENDS"]
}
```

### Neo4j Queries
```cypher
// Find direct friends
MATCH (p:Person {name: "Alice"})-[:FRIENDS]->(friend)
RETURN friend.name

// Find friends of friends
MATCH (p:Person {name: "Alice"})-[:FRIENDS]->(friend)-[:FRIENDS]->(friendOfFriend)
WHERE friendOfFriend <> p  // Exclude original person
RETURN DISTINCT friendOfFriend.name

// Find shortest path between two people
MATCH path = shortestPath((p1:Person {name: "Alice"})-[:FRIENDS*]-(p2:Person {name: "David"}))
RETURN path
```

## 2. Hierarchical Data (Company Structure)

### DOT Representation
```dot
digraph CompanyStructure {
    // Departments
    sales [label="Department", name="Sales"]
    marketing [label="Department", name="Marketing"]
    
    // Employees
    john [label="Employee", name="John", role="Manager"]
    mary [label="Employee", name="Mary", role="Team Lead"]
    pete [label="Employee", name="Pete", role="Associate"]
    
    // Relationships
    john -> mary [label="MANAGES"]
    mary -> pete [label="MANAGES"]
    john -> sales [label="WORKS_IN"]
    mary -> sales [label="WORKS_IN"]
    pete -> sales [label="WORKS_IN"]
}
```

### Neo4j Queries
```cypher
// Find all employees in a department
MATCH (d:Department {name: "Sales"})<-[:WORKS_IN]-(e:Employee)
RETURN e.name, e.role

// Find management chain for an employee
MATCH path = (e:Employee {name: "Pete"})<-[:MANAGES*]-(manager:Employee)
RETURN path

// Find all subordinates (direct and indirect)
MATCH (manager:Employee {name: "John"})-[:MANAGES*]->(subordinate:Employee)
RETURN subordinate.name, subordinate.role

// Find employees with their managers and departments
MATCH (e:Employee)-[:WORKS_IN]->(d:Department)
OPTIONAL MATCH (e)<-[:MANAGES]-(manager:Employee)
RETURN e.name, e.role, d.name as department, manager.name as manager_name
```

## 3. Time-Based Relationships (Project Timeline)

### DOT Representation
```dot
digraph ProjectTimeline {
    // Tasks
    planning [label="Task", name="Planning", duration="5d"]
    design [label="Task", name="Design", duration="10d"]
    development [label="Task", name="Development", duration="15d"]
    testing [label="Task", name="Testing", duration="7d"]
    
    // Dependencies
    planning -> design [label="PRECEDES", lag="0d"]
    design -> development [label="PRECEDES", lag="2d"]
    development -> testing [label="PRECEDES", lag="1d"]
}
```

### Neo4j Queries
```cypher
// Find all tasks and their dependencies
MATCH (t1:Task)-[r:PRECEDES]->(t2:Task)
RETURN t1.name, t2.name, r.lag

// Find critical path (tasks with no slack)
MATCH path = (start:Task)-[:PRECEDES*]->(end:Task)
WHERE NOT (start)<-[:PRECEDES]-()  // Start tasks
  AND NOT (end)-[:PRECEDES]->()    // End tasks
RETURN path

// Calculate total duration
MATCH (t:Task)
RETURN sum(toInteger(replace(t.duration, 'd', ''))) as total_days
```

## 4. Complex Relationships (Product Catalog)

### DOT Representation
```dot
digraph ProductCatalog {
    // Categories
    electronics [label="Category", name="Electronics"]
    phones [label="Category", name="Phones"]
    
    // Products
    iphone [label="Product", name="iPhone", price="999"]
    galaxy [label="Product", name="Galaxy", price="899"]
    
    // Features
    camera [label="Feature", name="Camera", specs="12MP"]
    battery [label="Feature", name="Battery", specs="4000mAh"]
    
    // Relationships
    electronics -> phones [label="HAS_SUBCATEGORY"]
    phones -> iphone [label="CONTAINS"]
    phones -> galaxy [label="CONTAINS"]
    iphone -> camera [label="HAS_FEATURE"]
    iphone -> battery [label="HAS_FEATURE"]
    galaxy -> camera [label="HAS_FEATURE"]
    galaxy -> battery [label="HAS_FEATURE"]
}
```

### Neo4j Queries
```cypher
// Find products in a category (including subcategories)
MATCH (c:Category {name: "Electronics"})-[:HAS_SUBCATEGORY*]->(sub:Category)-[:CONTAINS]->(p:Product)
RETURN p.name, p.price

// Find common features between products
MATCH (p1:Product {name: "iPhone"})-[:HAS_FEATURE]->(f:Feature)
MATCH (p2:Product {name: "Galaxy"})-[:HAS_FEATURE]->(f)
RETURN f.name, f.specs

// Find product details with all features
MATCH (p:Product)-[:HAS_FEATURE]->(f:Feature)
RETURN p.name, collect({feature: f.name, specs: f.specs}) as features

// Find categories and their product counts
MATCH (c:Category)-[:HAS_SUBCATEGORY*0..]->(sub:Category)-[:CONTAINS]->(p:Product)
RETURN c.name, count(DISTINCT p) as product_count
```

## 5. Pattern Matching (User Activity)

### DOT Representation
```dot
digraph UserActivity {
    // Users and content
    user1 [label="User", name="Alice"]
    post1 [label="Post", content="Hello"]
    post2 [label="Post", content="World"]
    comment1 [label="Comment", text="Nice!"]
    
    // Activities
    user1 -> post1 [label="CREATED", timestamp="2024-01-01"]
    user1 -> post2 [label="LIKED", timestamp="2024-01-02"]
    user1 -> comment1 [label="CREATED", timestamp="2024-01-03"]
    comment1 -> post2 [label="COMMENTS_ON"]
}
```

### Neo4j Queries
```cypher
// Find user's activity timeline
MATCH (u:User {name: "Alice"})-[activity]->()
RETURN type(activity), activity.timestamp
ORDER BY activity.timestamp

// Find posts with their comment counts
MATCH (p:Post)<-[:COMMENTS_ON]-(c:Comment)
RETURN p.content, count(c) as comment_count

// Find users who both created and liked content
MATCH (u:User)-[:CREATED]->(p1:Post)
MATCH (u)-[:LIKED]->(p2:Post)
RETURN DISTINCT u.name

// Find user's interaction patterns
MATCH (u:User)-[r]->(content)
WHERE type(content) IN ["Post", "Comment"]
RETURN u.name, type(content), type(r), count(*) as count
```

These patterns demonstrate:
1. Basic node and relationship creation
2. Complex queries with multiple conditions
3. Path finding and traversal
4. Aggregation and counting
5. Pattern matching with multiple relationship types
6. Time-based queries
7. Hierarchical data traversal

Would you like me to:
1. Add more specific use cases?
2. Explain any of these patterns in more detail?
3. Show how to optimize these queries?
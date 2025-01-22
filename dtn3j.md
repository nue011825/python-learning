This converter handles the following features:

Node Creation:

Converts DOT nodes to Neo4j nodes
Supports node labels and properties
Preserves node IDs as properties


Relationship Creation:

Converts DOT edges to Neo4j relationships
Supports relationship types and properties
Handles both directed and undirected relationships


Attribute Handling:

Parses DOT attributes into Neo4j properties
Special handling for 'label' attribute to set node labels or relationship types


# Create a converter instance
converter = DotToNeo4jConverter()

# Example DOT code
dot_code = """
digraph G {
    A [label="Person", name="John"]
    B [label="Company", name="Acme"]
    A -> B [label="WORKS_AT", role="Developer"]
}
"""

# Convert to Cypher
cypher_queries = converter.convert(dot_code)
print(cypher_queries)


The converter will generate Cypher queries like:

CREATE (:Person {name: 'John'});
CREATE (:Company {name: 'Acme'});
MATCH (from {name: 'A'}), (to {name: 'B'})
CREATE (from)-[:WORKS_AT {role: 'Developer'}]->(to);



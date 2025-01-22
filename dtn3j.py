import re
from typing import Dict, List, Tuple

class DotToNeo4jConverter:
    def __init__(self):
        self.nodes = {}
        self.relationships = []
        
    def parse_dot(self, dot_code: str) -> None:
        """Parse DOT code and extract nodes and relationships."""
        # Remove comments and clean up the code
        dot_code = re.sub(r'//.*?\n|/\*.*?\*/', '', dot_code, flags=re.DOTALL)
        dot_code = dot_code.strip()
        
        # Extract graph name and type
        graph_match = re.match(r'(strict\s+)?(di)?graph\s+(\w+)\s*{', dot_code)
        if not graph_match:
            raise ValueError("Invalid DOT format: Missing graph definition")
            
        # Process each line
        lines = dot_code.split('\n')
        for line in lines[1:-1]:  # Skip first and last lines (graph definition)
            line = line.strip()
            if not line or line.startswith('{'): continue
                
            # Handle node definitions
            node_match = re.match(r'(\w+)\s*\[(.*?)\]', line)
            if node_match:
                node_id, attrs = node_match.groups()
                self.nodes[node_id] = self._parse_attributes(attrs)
                continue
                
            # Handle relationships
            rel_match = re.match(r'(\w+)\s*(->|--)\s*(\w+)\s*(?:\[(.*?)\])?', line)
            if rel_match:
                from_node, rel_type, to_node, attrs = rel_match.groups()
                rel_attrs = self._parse_attributes(attrs) if attrs else {}
                self.relationships.append((from_node, to_node, rel_type, rel_attrs))
    
    def _parse_attributes(self, attrs_str: str) -> Dict:
        """Parse DOT attributes into a dictionary."""
        if not attrs_str:
            return {}
            
        attrs = {}
        pairs = re.findall(r'(\w+)\s*=\s*"([^"]*)"', attrs_str)
        for key, value in pairs:
            attrs[key] = value
        return attrs
    
    def generate_cypher(self) -> List[str]:
        """Generate Cypher queries from parsed DOT data."""
        queries = []
        
        # Create nodes
        for node_id, attrs in self.nodes.items():
            labels = attrs.get('label', '').split(':')
            primary_label = labels[0] if labels else 'Node'
            
            # Remove label from attributes if it was used for node type
            if 'label' in attrs and ':' in attrs['label']:
                del attrs['label']
            
            props = {k: v for k, v in attrs.items() if k != 'label'}
            props['name'] = node_id  # Add original node ID as a property
            
            query = f"CREATE (:{primary_label} {{"
            query += ', '.join(f"{k}: '{v}'" for k, v in props.items())
            query += "})"
            queries.append(query)
        
        # Create relationships
        for from_node, to_node, rel_type, attrs in self.relationships:
            rel_name = attrs.get('label', 'RELATES_TO')
            props = {k: v for k, v in attrs.items() if k != 'label'}
            
            query = f"""
            MATCH (from {{name: '{from_node}'}}), (to {{name: '{to_node}'}})
            CREATE (from)-[:{rel_name} {{"""
            query += ', '.join(f"{k}: '{v}'" for k, v in props.items())
            query += "}]->(to)"
            queries.append(query.strip())
        
        return queries

    def convert(self, dot_code: str) -> str:
        """Convert DOT code to Cypher queries."""
        self.parse_dot(dot_code)
        queries = self.generate_cypher()
        return ';\n'.join(queries) + ';'

# Example usage
if __name__ == "__main__":
    dot_code = """
    digraph G {
        A [label="Person:Employee", name="John"]
        B [label="Department", name="IT"]
        A -> B [label="WORKS_IN", since="2020"]
    }
    """
    
    converter = DotToNeo4jConverter()
    cypher_queries = converter.convert(dot_code)
    print(cypher_queries)
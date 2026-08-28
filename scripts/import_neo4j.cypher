CREATE CONSTRAINT hydraulic_node_id IF NOT EXISTS
FOR (n:KGNode) REQUIRE n.id IS UNIQUE;

// Option A: use the Python writer:
// python -m src.kg_building.write_neo4j

// Option B: import generated CSV manually after copying files into Neo4j import directory.
// LOAD CSV WITH HEADERS FROM 'file:///neo4j_nodes.csv' AS row
// MERGE (n:KGNode {id: row.id})
// SET n += row;
//
// LOAD CSV WITH HEADERS FROM 'file:///neo4j_relationships.csv' AS row
// MATCH (a:KGNode {id: row.source_id}), (b:KGNode {id: row.target_id})
// MERGE (a)-[r:RELATED {type: row.type}]->(b)
// SET r += row;

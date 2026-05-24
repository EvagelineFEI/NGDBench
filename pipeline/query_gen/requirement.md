1. Parameter Standardization
Issue: Inconsistent key naming within query templates (e.g., redundant use of L2 and Label2).

Action: Standardize all parameter keys. Replace shorthand or redundant keys with the full descriptive name: Label2.

Scope: Update all template definitions and any dictionaries/objects where these parameters are instantiated.

2. Sampling Logic Alignment
Issue: The sampling module currently relies on the old parameter naming convention.

Action: Update the query sampling logic to ensure it correctly maps values to the newly standardized Label2 keys.

3. Schema Constraint Enforcement (Critical)
Issue: The sampling module generates queries that are syntactically correct but semantically invalid according to the graph schema.

Example of invalid output: MATCH (n:Account) WHERE NOT (n)-[:Person_Invest_Company]->(:Account) RETURN count(n) (The relationship Person_Invest_Company does not connect Account nodes).

Action: Implement validation logic within the sampling module to ensure generated triplets (Source Label — Relationship — Target Label) strictly adhere to the schema.

Reference: Consult the definitions located in the /schema directory to enforce these constraints during the sampling process.
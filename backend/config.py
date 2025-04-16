from db.tabular.postgres_config import LoadPostgresConfig
from db.document.neo4j_config import LoadNeo4jConfig
from llm_core.llm_config import LoadOpenAIConfig


openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()
neo4j_var = LoadNeo4jConfig()
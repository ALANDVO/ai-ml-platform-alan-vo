from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    jwt_secret: str = "change-me-in-production-secret-key-32bytes"
    jwt_expiry_minutes: int = 60
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    saml_idp_entity: str = ""
    saml_idp_cert: str = ""
    saml_acs_url: str = ""
    saml_sp_entity: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_redirect_uri: str = ""
    data_dir: str = "data"
    checkpoint_dir: str = "checkpoints"
    max_concurrent_runs: int = 2
    batch_size: int = 16
    batch_timeout_ms: int = 50

settings = Settings(
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    jwt_secret=os.getenv("JWT_SECRET", "change-me-in-production-secret-key-32bytes"),
    jwt_expiry_minutes=int(os.getenv("JWT_EXPIRY_MINUTES", "60")),
    llm_api_key=os.getenv("LLM_API_KEY", ""),
    llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
    saml_idp_entity=os.getenv("SAML_IDP_ENTITY", ""),
    saml_idp_cert=os.getenv("SAML_IDP_CERT", ""),
    saml_acs_url=os.getenv("SAML_ACS_URL", ""),
    saml_sp_entity=os.getenv("SAML_SP_ENTITY", ""),
    oauth_client_id=os.getenv("OAUTH_CLIENT_ID", ""),
    oauth_client_secret=os.getenv("OAUTH_CLIENT_SECRET", ""),
    oauth_redirect_uri=os.getenv("OAUTH_REDIRECT_URI", ""),
    data_dir=os.getenv("DATA_DIR", "data"),
    checkpoint_dir=os.getenv("CHECKPOINT_DIR", "checkpoints"),
    max_concurrent_runs=int(os.getenv("MAX_CONCURRENT_RUNS", "2")),
    batch_size=int(os.getenv("BATCH_SIZE", "16")),
    batch_timeout_ms=int(os.getenv("BATCH_TIMEOUT_MS", "50")),
)

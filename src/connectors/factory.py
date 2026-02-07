"""
Factory pattern for creating ERP connectors.

Provides a centralized way to instantiate the appropriate connector based on ERP type.
"""

from typing import Any, Dict, Optional

from .base import ERPConnector, ERPType, ERPCredentials, AuthType
from .totvs_connector import TOTVSProtheusConnector
from .contaazul_connector import ContaAzulConnector
from .omie_connector import OmieConnector
from .bling_connector import BlingConnector


class ConnectorFactory:
    """Factory for creating ERP connector instances"""

    _connector_registry = {
        ERPType.TOTVS_PROTHEUS: TOTVSProtheusConnector,
        ERPType.CONTAAZUL: ContaAzulConnector,
        ERPType.OMIE: OmieConnector,
        ERPType.BLING: BlingConnector,
    }

    @classmethod
    def create_connector(
        cls,
        erp_type: ERPType,
        credentials: ERPCredentials,
        config: Optional[Dict[str, Any]] = None
    ) -> ERPConnector:
        """
        Create an ERP connector instance.

        Args:
            erp_type: Type of ERP system
            credentials: Authentication credentials
            config: Optional connector-specific configuration

        Returns:
            Configured ERPConnector instance

        Raises:
            ValueError: If ERP type is not supported
        """
        connector_class = cls._connector_registry.get(erp_type)

        if not connector_class:
            raise ValueError(
                f"Unsupported ERP type: {erp_type}. "
                f"Supported types: {list(cls._connector_registry.keys())}"
            )

        return connector_class(credentials, config)

    @classmethod
    def create_from_config(
        cls,
        config: Dict[str, Any]
    ) -> ERPConnector:
        """
        Create connector from configuration dictionary.

        Expected config format:
        {
            "erp_type": "totvs_protheus",
            "auth_type": "oauth2",
            "credentials": {
                "client_id": "...",
                "client_secret": "..."
            },
            "config": {
                "base_url": "...",
                "tenant": "..."
            }
        }

        Args:
            config: Configuration dictionary

        Returns:
            Configured ERPConnector instance
        """
        # Validate required fields
        required_fields = ["erp_type", "auth_type", "credentials"]
        missing = [f for f in required_fields if f not in config]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Parse ERP type
        erp_type_str = config["erp_type"]
        try:
            erp_type = ERPType(erp_type_str)
        except ValueError:
            raise ValueError(f"Invalid ERP type: {erp_type_str}")

        # Parse auth type
        auth_type_str = config["auth_type"]
        try:
            auth_type = AuthType(auth_type_str)
        except ValueError:
            raise ValueError(f"Invalid auth type: {auth_type_str}")

        # Create credentials
        credentials = ERPCredentials(
            auth_type=auth_type,
            credentials=config["credentials"],
            environment=config.get("environment", "production")
        )

        # Get additional config
        connector_config = config.get("config", {})

        return cls.create_connector(erp_type, credentials, connector_config)

    @classmethod
    def get_supported_erp_types(cls) -> list:
        """Get list of supported ERP types"""
        return list(cls._connector_registry.keys())

    @classmethod
    def register_connector(
        cls,
        erp_type: ERPType,
        connector_class: type
    ):
        """
        Register a custom connector class.

        Allows extending the factory with additional ERP connectors.

        Args:
            erp_type: ERP type identifier
            connector_class: Connector class (must inherit from ERPConnector)
        """
        if not issubclass(connector_class, ERPConnector):
            raise ValueError(
                f"{connector_class} must inherit from ERPConnector"
            )

        cls._connector_registry[erp_type] = connector_class


def create_connector(
    erp_type: str,
    auth_type: str,
    credentials: Dict[str, str],
    config: Optional[Dict[str, Any]] = None
) -> ERPConnector:
    """
    Convenience function to create a connector.

    Args:
        erp_type: ERP type string (e.g., "totvs_protheus")
        auth_type: Auth type string (e.g., "oauth2")
        credentials: Authentication credentials
        config: Optional configuration

    Returns:
        Configured ERPConnector instance

    Example:
        connector = create_connector(
            erp_type="totvs_protheus",
            auth_type="oauth2",
            credentials={
                "client_id": "your_client_id",
                "client_secret": "your_client_secret"
            },
            config={
                "base_url": "https://api.totvs.com.br",
                "tenant": "your_tenant_id"
            }
        )
    """
    config_dict = {
        "erp_type": erp_type,
        "auth_type": auth_type,
        "credentials": credentials,
        "config": config or {}
    }

    return ConnectorFactory.create_from_config(config_dict)


# Portfolio company to ERP mapping for reference
PORTFOLIO_COMPANY_ERP_MAPPING = {
    # TOTVS Protheus
    "effecti": ERPType.TOTVS_PROTHEUS,
    "onclick": ERPType.TOTVS_PROTHEUS,

    # ContaAzul
    "mercos": ERPType.CONTAAZUL,
    "munddi": ERPType.CONTAAZUL,

    # Omie
    "datahub": ERPType.OMIE,

    # Bling
    "ipe_digital": ERPType.BLING,
    "ipedigital": ERPType.BLING,
    "leadlovers": ERPType.BLING,
}


def get_erp_for_company(company_name: str) -> Optional[ERPType]:
    """
    Get ERP type for a portfolio company.

    Args:
        company_name: Portfolio company name (case-insensitive)

    Returns:
        ERPType if company is known, None otherwise
    """
    normalized_name = company_name.lower().replace(" ", "_")
    return PORTFOLIO_COMPANY_ERP_MAPPING.get(normalized_name)

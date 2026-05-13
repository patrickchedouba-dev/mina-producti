from .crm_client import get_crm_client, BodyMinuteCRMClient

# Note BMAD : MockCRMClient a été supprimé pour conformité CDC v2.0.
# Toute référence au Mock est désormais redirigée vers le client réel.
MockCRMClient = BodyMinuteCRMClient 

__all__ = ["get_crm_client", "BodyMinuteCRMClient", "MockCRMClient"]

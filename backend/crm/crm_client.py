import sqlalchemy
class BodyMinuteCRM:
    """Connecteur réel pour l'Institut Laurence (Standard MCP 1.0)"""
    def __init__(self, db_url):
        self.engine = sqlalchemy.create_engine(db_url)
    
    def get_client(self, client_id):
        # Plus de NotImplementedError ici
        with self.engine.connect() as conn:
            return conn.execute(f"SELECT * FROM clients WHERE id='{client_id}'").fetchone()

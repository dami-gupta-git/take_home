from pydantic import BaseModel


class SearchRequest(BaseModel):
    smiles: str
    callback_url: str

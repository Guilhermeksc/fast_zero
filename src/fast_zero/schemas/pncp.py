from pydantic import BaseModel, validator
import re

class ImportDescricaoItensRequest(BaseModel):
    cnpj: str
    sequencial: int
    ano: int

    @validator('cnpj')
    def validate_cnpj(cls, v):
        # Remove all non-numeric characters
        cnpj = re.sub(r'[^\d]', '', v)
        if len(cnpj) != 14:
            raise ValueError('CNPJ deve ter 14 dígitos')
        return cnpj

    @validator('sequencial')
    def validate_sequencial(cls, v):
        if v < 1 or v > 9999999999:
            raise ValueError('Sequencial deve ter até 10 dígitos')
        return v

    @validator('ano')
    def validate_ano(cls, v):
        if v < 1900 or v > 2100:
            raise ValueError('Ano inválido')
        return v 
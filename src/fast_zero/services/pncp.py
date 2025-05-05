import requests
import pandas as pd
from fastapi import HTTPException
from ..db.connection import get_conn
from io import BytesIO
from decimal import Decimal
from datetime import datetime

class PNCPService:
    @staticmethod
    def get_quantidade_itens(cnpj: str, sequencial: int, ano: int) -> int:
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/quantidade"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return int(response.text)
        except (requests.RequestException, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Erro ao consultar API do PNCP: {str(e)}")

    @staticmethod
    def validate_file(df: pd.DataFrame, n: int) -> None:
        # Verifica colunas obrigatórias
        required_columns = ['item', 'catalogo', 'descricao', 'descricao_detalhada']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Colunas obrigatórias faltando: {', '.join(missing_columns)}"
            )

        # Verifica quantidade de itens
        if len(df) > n:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo contém mais itens ({len(df)}) do que o permitido ({n})"
            )

        # Verifica sequência dos itens
        expected_items = set(range(1, n + 1))
        actual_items = set(df['item'].astype(int))
        missing_items = expected_items - actual_items
        if missing_items:
            raise HTTPException(
                status_code=400,
                detail=f"Itens faltando na sequência: {', '.join(map(str, sorted(missing_items)))}"
            )

    @staticmethod
    def save_descricao_itens(cnpj: str, sequencial: int, ano: int, df: pd.DataFrame) -> dict:
        with get_conn() as conn, conn.cursor() as cur:
            # Verifica se a compra existe
            cur.execute(
                "SELECT 1 FROM pncp WHERE sequencial_compra = %s AND ano_compra = %s",
                (sequencial, ano)
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Compra não encontrada na base de dados"
                )

            # Remove registros existentes
            items_to_update = [int(row['item']) for _, row in df.iterrows()]
            cur.execute(
                """
                DELETE FROM pncp_descricao_itens 
                WHERE cnpj = %s AND sequencial = %s AND ano = %s AND item = ANY(%s)
                """,
                (cnpj, sequencial, ano, items_to_update)
            )

            # Insere os novos registros
            for _, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO pncp_descricao_itens 
                    (cnpj, sequencial, ano, item, catalogo, descricao, descricao_detalhada)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cnpj,
                        sequencial,
                        ano,
                        int(row['item']),
                        row['catalogo'],
                        row['descricao'],
                        row['descricao_detalhada']
                    )
                )
            conn.commit()

        return {
            "message": "Arquivo importado com sucesso",
            "quantidade_itens": len(df),
            "itens_importados": len(df)
        }

    @staticmethod
    def get_pncp_data(cnpj: str | None, ano: int) -> pd.DataFrame:
        with get_conn() as conn, conn.cursor() as cur:
            if cnpj:
                cur.execute(
                    """
                    SELECT * FROM pncp 
                    WHERE sequencial_compra IN (
                        SELECT DISTINCT sequencial 
                        FROM pncp_descricao_itens 
                        WHERE cnpj = %s AND ano = %s
                    )
                    AND ano_compra = %s
                    ORDER BY sequencial_compra
                    """,
                    (cnpj, ano, ano)
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM pncp 
                    WHERE sequencial_compra IN (
                        SELECT DISTINCT sequencial 
                        FROM pncp_descricao_itens 
                        WHERE cnpj = '00394502000144' AND ano = %s
                    )
                    AND ano_compra = %s
                    ORDER BY sequencial_compra
                    """,
                    (ano, ano)
                )
            
            rows = cur.fetchall()
            
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="Nenhum dado encontrado para o CNPJ e ano informados"
                )
            
            # Converte os registros para um formato serializável
            serializable_rows = []
            for row in rows:
                serializable_row = {}
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        serializable_row[key] = float(value)
                    elif isinstance(value, (datetime, pd.Timestamp)):
                        serializable_row[key] = value.isoformat()
                    else:
                        serializable_row[key] = value
                serializable_rows.append(serializable_row)
            
            # Cria o DataFrame com todos os registros
            df = pd.DataFrame(serializable_rows)
            
            # Configura o pandas para mostrar todas as linhas
            pd.set_option('display.max_rows', None)
            
            return df 
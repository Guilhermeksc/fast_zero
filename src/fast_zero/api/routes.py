from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
from io import BytesIO
from ..schemas.pncp import ImportDescricaoItensRequest
from ..services.pncp import PNCPService

router = APIRouter()

@router.post(
    "/importar_descricao_itens",
    summary="Importar descrição de itens do PNCP"
)
async def importar_descricao_itens(
    cnpj: str,
    sequencial: int,
    ano: int,
    file: UploadFile = File(...)
):
    # 1) Valida os parâmetros
    request = ImportDescricaoItensRequest(cnpj=cnpj, sequencial=sequencial, ano=ano)
    cnpj = request.cnpj  # Usa o CNPJ já validado

    # 2) Consulta a API do PNCP
    n = PNCPService.get_quantidade_itens(cnpj, sequencial, ano)

    # 3) Valida o arquivo
    if not file.filename.endswith(('.xlsx', '.ods')):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx ou .ods")

    try:
        # Lê o arquivo
        df = pd.read_excel(file.file)
        
        # Valida o conteúdo do arquivo
        PNCPService.validate_file(df, n)

        # Salva os dados
        return PNCPService.save_descricao_itens(cnpj, sequencial, ano, df)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivo: {str(e)}")

@router.get(
    "/dados",
    summary="Baixar dados do PNCP em diferentes formatos"
)
async def get_pncp_data(
    ano: int,
    cnpj: str | None = None,
    formato: str = Query("json", enum=["json", "xlsx", "csv"])
):
    # Valida o CNPJ se fornecido
    validated_cnpj = None
    if cnpj:
        request = ImportDescricaoItensRequest(cnpj=cnpj, sequencial=1, ano=ano)
        validated_cnpj = request.cnpj  # Usa o CNPJ já validado

    # Obtém os dados
    df = PNCPService.get_pncp_data(validated_cnpj, ano)

    # Retorna no formato solicitado
    if formato == "json":
        return JSONResponse(content=df.to_dict(orient="records"))
    
    elif formato == "xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        
        filename = f"pncp_{validated_cnpj or '00394502000144'}_{ano}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    else:  # csv
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        filename = f"pncp_{validated_cnpj or '00394502000144'}_{ano}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        ) 
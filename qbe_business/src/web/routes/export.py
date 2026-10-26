import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.storage.database import get_db
from src.storage.models import PortfolioRecord
from src.reporting.compiler import ReportCompiler

router = APIRouter(prefix="/api/portfolio", tags=["Export"])

@router.get("/{portfolio_id}/pdf")
async def export_portfolio_pdf(portfolio_id: int, db: Session = Depends(get_db)):
    record = db.query(PortfolioRecord).filter(PortfolioRecord.id == portfolio_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Registro de cartera no encontrado")

    output_dir = os.path.join("data", "output")
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = f"qbe_report_portfolio_{portfolio_id}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    file_generated = ReportCompiler.compile(record.portfolio_json, Path(pdf_path))
    
    media_type = "application/pdf" if file_generated.endswith(".pdf") else "text/html"
    return FileResponse(file_generated, media_type=media_type, filename=os.path.basename(file_generated))

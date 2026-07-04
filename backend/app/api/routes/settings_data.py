from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.persona import Persona
from app.models.user import User
from app.services.data_management import clear_user_domain_data, utcnow_naive
from app.services.material_storage import remove_local_material_files
from app.services.memory_markdown import remove_memory_context_files


router = APIRouter(prefix="/settings", tags=["settings"])


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT)
def clear_current_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    persona_ids = db.scalars(select(Persona.id).where(Persona.user_id == current_user.id)).all()
    storage_urls = clear_user_domain_data(db, current_user, utcnow_naive())
    db.commit()
    remove_local_material_files(storage_urls)
    for persona_id in persona_ids:
        remove_memory_context_files(persona_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import BulkJob, BulkJobItem, User
from app.jobs.queue import enqueue
from app.schemas.jobs import BulkJobCreate, BulkJobDetailOut, BulkJobOut

MAX_PHOTO_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix="/api/bulk-jobs", tags=["bulk-jobs"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[BulkJobOut])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BulkJob).order_by(BulkJob.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=BulkJobDetailOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(BulkJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    result = await db.execute(select(BulkJobItem).where(BulkJobItem.job_id == job_id))
    items = list(result.scalars().all())
    return BulkJobDetailOut(**BulkJobOut.model_validate(job).model_dump(), items=items)


@router.post("", response_model=BulkJobOut)
async def create_job(
    payload: str = Form(...),
    photo: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = BulkJobCreate.model_validate_json(payload)
    if not data.account_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "대상 계정을 선택하세요.")

    payload_template: dict = {}
    if data.first_name is not None:
        payload_template["first_name"] = data.first_name
    if data.last_name is not None:
        payload_template["last_name"] = data.last_name
    if data.bio is not None:
        payload_template["bio"] = data.bio
    if data.username is not None:
        payload_template["username"] = data.username

    if photo is not None:
        photo_bytes = await photo.read()
        if len(photo_bytes) > MAX_PHOTO_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "사진 파일이 너무 큽니다.")
        payload_template["photo_base64"] = base64.b64encode(photo_bytes).decode()

    if not payload_template:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "변경할 항목을 하나 이상 입력하세요.")

    job = BulkJob(
        job_type="bulk_profile_update",
        status="pending",
        payload_template=payload_template,
        created_by=user.id,
        total_items=len(data.account_ids),
    )
    db.add(job)
    await db.flush()

    items = [
        BulkJobItem(
            job_id=job.id,
            account_id=account_id,
            payload_override=(data.per_account or {}).get(account_id),
            status="pending",
        )
        for account_id in data.account_ids
    ]
    db.add_all(items)
    await db.commit()
    await db.refresh(job)
    for item in items:
        await db.refresh(item)

    for item in items:
        await enqueue(item.id)

    return job

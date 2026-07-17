from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List
from uuid import UUID
import pandas as pd
import io
import json

from app.api.deps import get_current_user
from app.db.session import get_db
from app.core.cache import get_redis
from app.models.user import User
from app.models.uploaded_file import UploadedFile
from app.models.attendance_record import AttendanceRecord

router = APIRouter()

# ADMIN / HR ONLY

# upload excel, parse, store
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Upload excel"""
    # check if user has perms
    if "write:attendance" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No write:attendance permission"
        )
    
    # check if filename exists already
    existing_file = await db.execute(
        select(UploadedFile).where(UploadedFile.filename == file.filename)
    )

    if existing_file.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}' has already been uploaded" 
        )

    # read and parse excel
    contents = await file.read()

    df = pd.read_excel(
        io.BytesIO(contents),
        engine="openpyxl"
    )
    df.columns = df.columns.str.strip()

    # create UploadedFile record
    uploaded_file = UploadedFile(
        filename=file.filename,
        uploaded_by=current_user.id
    )
    db.add(uploaded_file)
    await db.flush() # get file ID

    # parse and create AttendanceRecord entries
    records_created = 0
    for _, row in df.iterrows():
        name = row.get("姓名")
        hours = row.get("打卡时长")
        date = row.get("日期")

        if pd.isna(name) or pd.isna(hours):
            continue

        hours = pd.to_numeric(hours, errors="coerce")
        if pd.isna(hours):
            continue

        user_name = str(name).strip()
        hours_worked = float(hours)

        # Convert to timezone-aware datetime
        if not pd.isna(date):
            attendance_date = pd.to_datetime(date).tz_localize('UTC')
        else:
            from datetime import datetime, timezone
            attendance_date = datetime.now(timezone.utc)

        # Check if record already exists for this user and date
        existing_record = await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.file_id == uploaded_file.id,
                AttendanceRecord.user_name == user_name,
                AttendanceRecord.date == attendance_date
            )
        )
        existing = existing_record.scalar_one_or_none()

        if existing:
            # Sum the hours
            existing.hours_worked += hours_worked
        else:
            # Create new attendance record
            attendance_record = AttendanceRecord(
                file_id=uploaded_file.id,
                user_name=user_name,
                hours_worked=hours_worked,
                date=attendance_date
            )
            db.add(attendance_record)
            records_created += 1

    await db.commit()

    # delete cache
    cache_key = "attendance:upload_metadata"
    await redis_client.delete(cache_key)

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "records_created": records_created
    }

# view all attendance
@router.post("/")
async def get_attendance(
    names: List[str] = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance data for specified names."""
    # Check if user has perms
    if "read:attendance" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No read:attendance permissions"
        )

    # query attendance records from db
    result = await db.execute(
        select(AttendanceRecord.user_name, 
               func.sum(AttendanceRecord.hours_worked).label("total_hours"), 
               func.max(AttendanceRecord.date).label("date"))
        .where(AttendanceRecord.user_name.in_(names))
        .group_by(AttendanceRecord.user_name)
    )

    rows = result.all()
    data = [
        {
            "name": row.user_name,
            "total_hours": round(row.total_hours, 2),
            "date": row.date.isoformat() if row.date else None,
        }
        for row in rows
    ]

    return {"data": data}


# export to excel
@router.post("/export")
async def export_attendance(
    names: list[str] = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export attendance data to Excel format."""
    # Check permissions 
    if "export:attendance" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No export:attendance permission"
        )

    result = await db.execute(
        select(AttendanceRecord.user_name, 
               func.sum(AttendanceRecord.hours_worked).label("total_hours"), 
               func.max(AttendanceRecord.date).label("date"))
        .where(AttendanceRecord.user_name.in_(names))
        .group_by(AttendanceRecord.user_name)
    )

    rows = result.all()
    data = [
        {
            "name": row.user_name,
            "total_hours": round(row.total_hours, 2),
            "date": row.date.isoformat() if row.date else None,
        }
        for row in rows
    ]

    df_out = pd.DataFrame(data).rename(columns={
        "name": "姓名",
        "total_hours": "打卡时长",
        "date": "日期"
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Attendance")

    buffer.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename=attendance_export.xlsx"
    }

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    if "write:attendance" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No write:attendance permission"
        )
    
    uploaded_file = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.id == file_id)
    )

    attendance_record = await db.execute(
        delete(AttendanceRecord)
        .where(AttendanceRecord.file_id == file_id)
    )

    uploaded_file = uploaded_file.scalar_one_or_none()

    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    await db.delete(uploaded_file)
    await db.commit()

    # delete cache
    cache_key = "attendance:upload_metadata"
    await redis_client.delete(cache_key)

    return {
        "message": "Uploaded file deleted successfully",
        "filename": uploaded_file.filename
    }

# metadata 
@router.get("/metadata")
async def get_metadata(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    # check if user has perms
    if "write:attendance" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No write:attendance permission"
        )

    # check if in cache
    cache_key = "attendance:upload_metadata"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query with join to get uploader's name
    result = await db.execute(
        select(UploadedFile, User.full_name)
        .join(User, UploadedFile.uploaded_by == User.id)
        .order_by(UploadedFile.uploaded_at.desc())
    )

    rows = result.all()
    data = [
        {
            "id": str(file.id),
            "filename": file.filename,
            "uploaded_by": uploader_name,
            "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else None
        }
        for file, uploader_name in rows
    ]

    await redis_client.setex(cache_key, 60, json.dumps({"data": data}))

    return {"data": data}


# ALL AUTHENTICATED USERS
# users can see their own total hours 
@router.get("/me")
async def get_self_attendance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AttendanceRecord.user_name,
               func.sum(AttendanceRecord.hours_worked).label("total_hours"),
               func.max(AttendanceRecord.date).label("date")
        )
        .where(AttendanceRecord.user_name == current_user.full_name)
        .group_by(AttendanceRecord.user_name)
    )

    rows = result.all()
    data = [
        {
            "name": row.user_name,
            "total_hours": round(row.total_hours, 2),
            "date": row.date.isoformat() if row.date else None
        }
        for row in rows
    ]

    return {"data": data}

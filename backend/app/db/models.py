from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy import JSON as SAJSON
from sqlalchemy.sql import func
from .session import Base
from sqlalchemy import Index

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    dataset_id = Column(String, unique=True, index=True)
    path = Column(String)
    version = Column(Integer)
    num_cases = Column(Integer)
    # 'metadata' is a reserved attribute name on Declarative base (Base.metadata).
    # Use a different column name to avoid SQLAlchemy InvalidRequestError.
    metadata_json = Column(SAJSON)
    created_at = Column(DateTime, server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    job_id = Column(String, unique=True, index=True)
    dataset_id = Column(String, index=True)
    status = Column(String, index=True)
    num_cases = Column(Integer)
    mode = Column(String)
    meta = Column(SAJSON)
    created_at = Column(DateTime, server_default=func.now())


class CaseResult(Base):
    __tablename__ = "case_results"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    job_id = Column(String, index=True)
    case_id = Column(String, index=True)
    engine_id = Column(String)
    aggregated_score = Column(Float)
    scores = Column(SAJSON)
    raw = Column(SAJSON)
    status = Column(String)
    evaluated_at = Column(DateTime, server_default=func.now())


Index("ix_case_job_case", CaseResult.job_id, CaseResult.case_id)

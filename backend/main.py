from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query
from contextlib import asynccontextmanager
from logging import INFO, basicConfig, getLogger

import os
from dotenv import load_dotenv

#this is to test out the basic api, will split it post setup
class JournalBase(SQLModel):
    page_title: str | None=Field(default=None)
    page_content: str | None=Field(default=None)

#public data model, we let user only interact with the page_title and page_content and nothing else
class Journal(JournalBase, table=True):
    page_id: int | None = Field(index=True, primary_key=True)
    page_created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JournalPublic(JournalBase):
    page_id: int

#new class to validate data
class JournalCreate(JournalBase):
    page_title: str
    page_content: str

class JournalUpdate(JournalBase):
    page_title: str | None = None
    page_content: str | None = None
    page_created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

logger = getLogger(__name__)
basicConfig(level=INFO)

#import db url from .env
load_dotenv()
DATABASE_URL="postgresql://postgres:1234@localhost:5433/journalDB"

#initialize the engine
engine=create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
    
SessionDep = Annotated[Session, Depends(get_session)]

#calls any functions required duing startup/shutdown
#in this case, we call create_db_and_tables, to create the tables for our use case.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    create_db_and_tables()
    yield
    logger.info("Shutting down...")
    logger.info("Finished shutting down.")

#initialize an instance of fastapi
app = FastAPI(lifespan=lifespan)

def get_session():
    with Session(engine) as session:
        yield session


#---------------------------------------------------
#---------------#             #---------------------
##--------------#API ENDPOINTS#---------------------
#---------------#             #---------------------
#---------------------------------------------------

@app.post("/")
def homepage():
    return {"message": "the db works??"}

#create a new journal
@app.post("/createjournal/", response_model=JournalPublic)
def create_journal(journal: Journal, session: SessionDep) -> Journal:
    db_journal = Journal.model_validate(journal)
    session.add(db_journal)
    session.commit()
    session.refresh(db_journal)
    return db_journal

#return all pages of the journal
@app.get("/getjournals/", response_model=list[JournalPublic])
def read_journal(session: SessionDep, 
                 offset: int=0, 
                 limit: Annotated[int, Query(le=100)]=100,
                 ) -> list[Journal]:
    journals = session.exec(select(Journal).offset(offset).limit(limit)).all()
    return journals

#return individual journal
@app.get("/getjournals/{page_id}", response_model=JournalPublic)
def read_journal(page_id, session: SessionDep):
    journal = session.get(Journal, page_id)
    if not journal:
        raise HTTPException(status_code=404, detail="journal not found")
    return journal

#delete individial page of the journal
@app.delete("/deletejournal/{page_id}")
def delete_journal(page_id: int, session: SessionDep):
    journal = session.get(Journal, page_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Page not found")
    session.delete(journal)
    session.commit()
    return {"ok": True}

#update journal
@app.patch("/journals/{page_id}", response_model=JournalPublic)
def update_journal(page_id: int, journal: JournalUpdate, session: SessionDep):
    journal_db = session.get(Journal, page_id)
    if not journal_db:
        raise HTTPException(status_code=404, detail="page not found")
    journal_data = journal.model_dump(exclude_unset=True)
    journal_db.sqlmodel_update(journal_data)
    session.add(journal_db)
    session.commit()
    session.refresh(journal_db)
    return journal_db

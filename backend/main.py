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

#public data model, we only let 
class Journal(JournalBase, table=True):
    page_id: int | None = Field(index=True, primary_key=True)
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
@app.post("/createjournal/")
def create_journal(journal: Journal, session: SessionDep) -> Journal:
    session.add(journal)
    session.commit()
    session.refresh(journal)
    return journal

#return all pages of the journal
@app.get("/getjournals/")
def read_journal(session: SessionDep, 
                 offset: int=0, 
                 limit: Annotated[int, Query(le=100)]=100,
                 ) -> list[Journal]:
    journals = session.exec(select(Journal).offset(offset).limit(limit)).all()
    return journals

#delete individial page of the journal
@app.delete("/deletejournal/{page_id}")
def delete_journal(page_id: int, session: SessionDep):
    journal = session.get(Journal, page_id)

    if not journal:
        raise HTTPException(status_code=404, detail="Page not found")
    session.delete(journal)
    session.commit()
    return {"ok": True}
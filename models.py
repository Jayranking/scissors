from Database.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)



class Url(Base):
    __tablename__ = 'urls'  

    id = Column(Integer, primary_key=True, index=True)
    short_id = Column(String, index=True, unique=True)
    long_url = Column(String)
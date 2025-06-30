import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Welcome(Base):
    __tablename__ = 'welcome'
    id      = sa.Column(sa.Integer, primary_key=True)
    chat_id = sa.Column(sa.BigInteger, index=True, nullable=False)
    text    = sa.Column(sa.Text, nullable=False)

engine = sa.create_engine('sqlite:///bot.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

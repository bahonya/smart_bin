from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy import create_engine, desc
from random import getrandbits


engine = create_engine("sqlite:///smart_bin.db", echo=True)
Base = declarative_base()
Session = sessionmaker(engine)

class FlatShare(Base):
    __tablename__ = "flat_share"
    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    inhabitants = relationship("Inhabitant")
    garbagebins = relationship("GarbageBin")

    def __repr__(self):
        return f"flat_share(id={self.id!r}, name={self.name!r}"

class Inhabitant(Base):
    __tablename__ = "inhabitants"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, nullable=False)
    name = Column(String(30), nullable=False)
    flat_share_id = Column(Integer, ForeignKey('flat_share.id'))
    flat_share = relationship('FlatShare', back_populates='inhabitants')

    def __repr__(self):
        return f'Inhabitant(id={self.id!r}, chat_id={self.chat_id!r}, name={self.name!r})'

class GarbageBin(Base):
    __tablename__ = "garbagebins"
    id = Column(Integer, primary_key=True)
    garbage_bin_id = Column(String(30), nullable=False)
    name = Column(String(30), nullable=False)
    state = Column(Boolean, default=False)
    flat_share_id = Column(Integer, ForeignKey('flat_share.id'))
    flat_share = relationship('FlatShare', back_populates='garbagebins')

    def __repr__(self):
        return f'Garbage bin (db id={self.id!r}, garbage bin id={self.garbage_bin_id!r})'


class Duty(Base):
    __tablename__ = 'duties'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    flat_share_id = Column(Integer, ForeignKey('flat_share.id'))
    inhabitant_id = Column(Integer, ForeignKey('inhabitants.id'))

    def __repr__(self):
        return f'Duty (db id={self.id!r}, duty description id={self.name!r})'

Base.metadata.create_all(engine,checkfirst=True)

def create_wg(name):
    with Session.begin() as session:
        new_wg = FlatShare(name=name)
        session.add(new_wg)
        session.flush()
        id = new_wg.id
        session.commit()
    return id

def add_inhabitant(chat_id, name, flat_share_id):
    with Session.begin() as session:
        new_inhabitant = Inhabitant(chat_id=chat_id, name=name, flat_share_id=flat_share_id)
        session.add(new_inhabitant)
        session.commit()

def user_is_in_wg(chat_id):
    with Session.begin() as session:
        exists = session.query(Inhabitant.chat_id).filter_by(chat_id=chat_id).first() is not None
    return exists


def add_garbage_bin(garbage_bin_id, name, state, flat_share_id):
    with Session.begin() as session:
        new_garbage_bin = GarbageBin(garbage_bin_id=garbage_bin_id, name=name, state=state, flat_share_id=flat_share_id)
        session.add(new_garbage_bin)
        session.commit()

def add_completed_duty(chat_id, name):
    with Session.begin() as session:
        flat_share_id = session.query(Inhabitant.flat_share_id).filter_by(chat_id=chat_id).first()[0]
        new_completed_duty = Duty(name=name, timestamp=func.now(), flat_share_id=flat_share_id, inhabitant_id=chat_id)
        session.add(new_completed_duty)
        session.commit()

def get_bins_states(chat_id):
    with Session.begin() as session:
        flat_share_id = session.query(Inhabitant.flat_share_id).filter_by(chat_id=chat_id).first()[0]
        states = session.query(GarbageBin.state, GarbageBin.name).filter_by(flat_share_id=flat_share_id).all()
    return states

def get_top10_duties(chat_id):
    with Session.begin() as session:
        flat_share_id = session.query(Inhabitant.flat_share_id).filter_by(chat_id=chat_id).first()[0]
        duties = session.query(Duty.name, Duty.timestamp).filter_by(flat_share_id=flat_share_id).\
            order_by(desc(Duty.timestamp)).limit(10).all()
    return duties

def change_bin_state(flat_share_id):
    with Session.begin() as session:
        session.query(GarbageBin).filter(GarbageBin.flat_share_id == flat_share_id).update({True: False, False: True})
        session.commit()

#me="309972156"
#create_wg("Someone's WG")
#add_garbage_bin(garbage_bin_id="place for papier's key in the payload", name="Papier", state=False, flat_share_id=1)
#[print(state,name) for state, name in get_bins_states("309972156")]
#add_completed_duty(chat_id=me, name="Bakytzhan has thrown Papier")
#print(get_top10_duties(me))
#print(get_bins_states(me))
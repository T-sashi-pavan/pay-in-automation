from sqlalchemy import Column, String
from backend.app.database.session import Base


class MasterState(Base):
    __tablename__ = "master_states"

    code = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)


class MasterProduct(Base):
    __tablename__ = "master_products"

    code = Column(String(20), primary_key=True)
    name = Column(String(200), nullable=False)


class MasterVehicleType(Base):
    __tablename__ = "master_vehicle_types"

    code = Column(String(20), primary_key=True)
    name = Column(String(200), nullable=False)


class MasterPolicyType(Base):
    __tablename__ = "master_policy_types"

    code = Column(String(20), primary_key=True)
    name = Column(String(200), nullable=False)

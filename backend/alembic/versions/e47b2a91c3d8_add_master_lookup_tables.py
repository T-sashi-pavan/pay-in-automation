"""add_master_lookup_tables

Revision ID: e47b2a91c3d8
Revises: 7f2a9d3e6c41
Create Date: 2026-07-10 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert


# revision identifiers, used by Alembic.
revision: str = 'e47b2a91c3d8'
down_revision: Union[str, None] = '7f2a9d3e6c41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STATES = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CG": "Chhattisgarh", "CT": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JH": "Jharkhand", "KA": "Karnataka",
    "KL": "Kerala", "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur",
    "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "OR": "Odisha",
    "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
    "TG": "Telangana", "TS": "Telangana", "TR": "Tripura", "UP": "Uttar Pradesh",
    "UK": "Uttarakhand", "UA": "Uttarakhand", "UT": "Uttarakhand", "WB": "West Bengal",
    "AN": "Andaman and Nicobar Islands", "CH": "Chandigarh", "DN": "Dadra and Nagar Haveli",
    "DD": "Daman and Diu", "DL": "Delhi", "JK": "Jammu and Kashmir", "LA": "Ladakh",
    "LD": "Lakshadweep", "PY": "Puducherry", "ALL": "All India",
}

PRODUCTS = {
    "GCV": "Goods Carrying Vehicle",
    "GCCV": "Goods Carrying Commercial Vehicle",
    "PC [SOD]": "Private Car (Standalone Own Damage)",
    "PC": "Private Car",
    "MC": "Motor Cycle",
    "TW": "Two Wheeler",
    "MSV": "Medium Service Vehicle",
    "LCV": "Light Commercial Vehicle",
    "HCV": "Heavy Commercial Vehicle",
    "SUV": "Sports Utility Vehicle",
    "MUV": "Multi Utility Vehicle",
}

# Starter sets only — extensible later via additive upserts, not exhaustive.
VEHICLE_TYPES = {
    "GCV": "Goods Carrying Vehicle",
    "LCV": "Light Commercial Vehicle",
    "HCV": "Heavy Commercial Vehicle",
    "MHCV": "Medium and Heavy Commercial Vehicle",
    "PCV": "Passenger Carrying Vehicle",
}

POLICY_TYPES = {
    "ACT": "Act Only (Third Party)",
    "PACK": "Package",
    "COMP": "Comprehensive",
    "SAOD": "Standalone Own Damage",
    "STP": "Standalone Third Party",
    "TP": "Third Party",
    "P": "Package",
    "P & L": "Package and Liability",
}


def _seed(table_name: str, data: dict) -> None:
    table = sa.table(table_name, sa.column("code", sa.String), sa.column("name", sa.String))
    rows = [{"code": code, "name": name} for code, name in data.items()]
    stmt = pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["code"])
    op.execute(stmt)


def upgrade() -> None:
    op.create_table(
        'master_states',
        sa.Column('code', sa.String(length=10), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
    )
    op.create_table(
        'master_products',
        sa.Column('code', sa.String(length=20), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
    )
    op.create_table(
        'master_vehicle_types',
        sa.Column('code', sa.String(length=20), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
    )
    op.create_table(
        'master_policy_types',
        sa.Column('code', sa.String(length=20), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
    )

    _seed('master_states', STATES)
    _seed('master_products', PRODUCTS)
    _seed('master_vehicle_types', VEHICLE_TYPES)
    _seed('master_policy_types', POLICY_TYPES)


def downgrade() -> None:
    op.drop_table('master_policy_types')
    op.drop_table('master_vehicle_types')
    op.drop_table('master_products')
    op.drop_table('master_states')

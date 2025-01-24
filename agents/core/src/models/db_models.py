from datetime import datetime
from sqlalchemy import MetaData, Table, Column, Integer, DateTime, String, Float, JSON, Boolean
from alembic import op
import os
from dotenv import load_dotenv

# Create metadata object
metadata = MetaData()

# Define the metrics table
metrics = Table(
    'metrics',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('timestamp', DateTime, nullable=False),
    Column('metric_name', String(50), nullable=False),
    Column('value', Float, nullable=False),
    Column('metadata', JSON),
    Column('is_training_data', Boolean, default=False),
)

def upgrade():
    op.create_table(
        'metrics',
        Column('id', Integer, primary_key=True),
        Column('timestamp', DateTime, nullable=False),
        Column('metric_name', String(50), nullable=False),
        Column('value', Float, nullable=False),
        Column('metadata', JSON),
        Column('is_training_data', Boolean, default=False),
    )
    
    op.create_index('idx_metrics_timestamp', 'metrics', ['timestamp'])
    op.create_index('idx_metrics_name', 'metrics', ['metric_name'])
    op.create_index('idx_metrics_training', 'metrics', ['is_training_data'])

def downgrade():
    op.drop_table('metrics')
